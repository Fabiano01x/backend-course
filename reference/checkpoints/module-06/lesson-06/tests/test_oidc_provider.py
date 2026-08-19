from datetime import UTC, datetime, timedelta
import base64
from urllib.parse import parse_qs, urlsplit

from cryptography.hazmat.primitives.asymmetric import rsa
import httpx
import jwt
import pytest

from app.config import Settings
from app.integrations.oidc import HttpOidcProvider, OidcProviderError
from app.security.oidc import base64url_sha256, digest_secret


pytestmark = pytest.mark.anyio
ISSUER = "https://idp.example"
CLIENT_ID = "library-web"
NONCE = "nonce-specific-to-this-browser"


def base64url_integer(value: int) -> str:
    length = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(length, "big")).rstrip(b"=").decode()


def provider_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        oidc_issuer=ISSUER,
        oidc_client_id=CLIENT_ID,
        oidc_client_secret="external-client-secret",
        oidc_redirect_uri="http://test/auth/oidc/callback",
    )


def oidc_transport(*, nonce: str = NONCE, discovery_issuer: str = ISSUER):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": "key-1",
        "n": base64url_integer(public_numbers.n),
        "e": base64url_integer(public_numbers.e),
    }
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": discovery_issuer,
                    "authorization_endpoint": f"{ISSUER}/authorize",
                    "token_endpoint": f"{ISSUER}/token",
                    "jwks_uri": f"{ISSUER}/jwks",
                    "id_token_signing_alg_values_supported": ["RS256"],
                    "code_challenge_methods_supported": ["S256"],
                },
            )
        if request.url.path == "/token":
            seen["authorization"] = request.headers.get("authorization")
            seen["form"] = parse_qs(request.content.decode())
            now = datetime.now(UTC).replace(microsecond=0)
            id_token = jwt.encode(
                {
                    "iss": ISSUER,
                    "sub": "subject-123",
                    "aud": CLIENT_ID,
                    "iat": now,
                    "exp": now + timedelta(minutes=5),
                    "nonce": nonce,
                    "email": "ADA@EXAMPLE.COM",
                    "email_verified": True,
                    "name": "Ada Lovelace",
                },
                private_key,
                algorithm="RS256",
                headers={"kid": "key-1"},
            )
            return httpx.Response(200, json={"id_token": id_token})
        if request.url.path == "/jwks":
            return httpx.Response(200, json={"keys": [jwk]})
        return httpx.Response(404)

    return httpx.MockTransport(handler), seen


async def test_builds_authorization_code_request_with_nonce_state_and_pkce() -> None:
    transport, _ = oidc_transport()
    async with httpx.AsyncClient(transport=transport) as client:
        provider = HttpOidcProvider(provider_settings(), client)
        url = await provider.authorization_url(
            state="state-123",
            nonce=NONCE,
            code_challenge=base64url_sha256("verifier-123"),
        )

    query = parse_qs(urlsplit(url).query)
    assert urlsplit(url).path == "/authorize"
    assert query == {
        "response_type": ["code"],
        "client_id": [CLIENT_ID],
        "redirect_uri": ["http://test/auth/oidc/callback"],
        "scope": ["openid email profile"],
        "state": ["state-123"],
        "nonce": [NONCE],
        "code_challenge": [base64url_sha256("verifier-123")],
        "code_challenge_method": ["S256"],
    }


async def test_exchanges_code_with_basic_auth_and_validates_signed_id_token() -> None:
    transport, seen = oidc_transport()
    async with httpx.AsyncClient(transport=transport) as client:
        claims = await HttpOidcProvider(
            provider_settings(), client
        ).exchange_code(
            code="authorization-code",
            code_verifier="verifier-123",
            expected_nonce_digest=digest_secret(NONCE),
        )

    assert claims.issuer == ISSUER
    assert claims.subject == "subject-123"
    assert claims.email == "ADA@EXAMPLE.COM"
    assert claims.email_verified is True
    assert str(seen["authorization"]).startswith("Basic ")
    assert seen["form"] == {
        "grant_type": ["authorization_code"],
        "code": ["authorization-code"],
        "redirect_uri": ["http://test/auth/oidc/callback"],
        "code_verifier": ["verifier-123"],
    }


async def test_rejects_nonce_mismatch_and_discovery_issuer_substitution() -> None:
    transport, _ = oidc_transport()
    async with httpx.AsyncClient(transport=transport) as client:
        provider = HttpOidcProvider(provider_settings(), client)
        with pytest.raises(OidcProviderError, match="nonce"):
            await provider.exchange_code(
                code="authorization-code",
                code_verifier="verifier-123",
                expected_nonce_digest=digest_secret("another-nonce"),
            )

    substituted, _ = oidc_transport(discovery_issuer="https://attacker.example")
    async with httpx.AsyncClient(transport=substituted) as client:
        with pytest.raises(OidcProviderError, match="issuer"):
            await HttpOidcProvider(provider_settings(), client).authorization_url(
                state="state", nonce=NONCE, code_challenge="challenge"
            )
