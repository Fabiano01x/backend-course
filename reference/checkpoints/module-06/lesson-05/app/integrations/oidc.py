"""Cliente OIDC estrito para discovery, code exchange e ID Token."""

from dataclasses import dataclass
import hmac
from typing import Protocol
from urllib.parse import urlencode, urlsplit

import httpx
import jwt
from jwt import InvalidTokenError

from app.config import Settings
from app.security.oidc import digest_secret


OIDC_ID_TOKEN_ALGORITHM = "RS256"


class OidcProviderError(Exception):
    """O provedor não apresentou uma resposta OIDC confiável."""

    def __init__(self, detail: str, *, unavailable: bool = False) -> None:
        super().__init__(detail)
        self.unavailable = unavailable


@dataclass(frozen=True, slots=True)
class OidcClaims:
    issuer: str
    subject: str
    email: str | None
    email_verified: bool
    name: str | None


@dataclass(frozen=True, slots=True)
class OidcMetadata:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str


class OidcProvider(Protocol):
    async def authorization_url(
        self,
        *,
        state: str,
        nonce: str,
        code_challenge: str,
    ) -> str: ...

    async def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
        expected_nonce_digest: str,
    ) -> OidcClaims: ...


def require_https_url(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise OidcProviderError(f"metadata OIDC sem {field}")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise OidcProviderError(f"metadata OIDC possui {field} inseguro")
    return value


class HttpOidcProvider:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        if not settings.oidc_enabled:
            raise OidcProviderError("OpenID Connect não configurado")
        self.settings = settings
        self.client = client
        self._metadata: OidcMetadata | None = None

    async def metadata(self) -> OidcMetadata:
        if self._metadata is not None:
            return self._metadata
        issuer = self.settings.oidc_issuer or ""
        discovery_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
        try:
            response = await self.client.get(discovery_url)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPError as error:
            raise OidcProviderError(
                "discovery OIDC indisponível", unavailable=True
            ) from error
        except ValueError as error:
            raise OidcProviderError("discovery OIDC inválido") from error
        if not isinstance(body, dict) or body.get("issuer") != issuer:
            raise OidcProviderError("issuer do discovery não corresponde ao configurado")
        supported_algorithms = body.get("id_token_signing_alg_values_supported", [])
        if OIDC_ID_TOKEN_ALGORITHM not in supported_algorithms:
            raise OidcProviderError("provedor não oferece RS256 para ID Token")
        if "S256" not in body.get("code_challenge_methods_supported", []):
            raise OidcProviderError("provedor não declara PKCE S256")
        self._metadata = OidcMetadata(
            issuer=issuer,
            authorization_endpoint=require_https_url(
                body.get("authorization_endpoint"), "authorization_endpoint"
            ),
            token_endpoint=require_https_url(
                body.get("token_endpoint"), "token_endpoint"
            ),
            jwks_uri=require_https_url(body.get("jwks_uri"), "jwks_uri"),
        )
        return self._metadata

    async def authorization_url(
        self,
        *,
        state: str,
        nonce: str,
        code_challenge: str,
    ) -> str:
        metadata = await self.metadata()
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.settings.oidc_client_id or "",
                "redirect_uri": self.settings.oidc_redirect_uri or "",
                "scope": "openid email profile",
                "state": state,
                "nonce": nonce,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{metadata.authorization_endpoint}?{query}"

    async def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
        expected_nonce_digest: str,
    ) -> OidcClaims:
        metadata = await self.metadata()
        try:
            token_response = await self.client.post(
                metadata.token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.settings.oidc_redirect_uri or "",
                    "code_verifier": code_verifier,
                },
                auth=httpx.BasicAuth(
                    self.settings.oidc_client_id or "",
                    self.settings.oidc_client_secret.get_secret_value()
                    if self.settings.oidc_client_secret is not None
                    else "",
                ),
            )
            token_response.raise_for_status()
            token_body = token_response.json()
        except httpx.HTTPStatusError as error:
            raise OidcProviderError(
                "troca do authorization code falhou",
                unavailable=error.response.status_code >= 500,
            ) from error
        except httpx.RequestError as error:
            raise OidcProviderError(
                "token endpoint indisponível", unavailable=True
            ) from error
        except ValueError as error:
            raise OidcProviderError("troca do authorization code falhou") from error
        id_token = token_body.get("id_token") if isinstance(token_body, dict) else None
        if not isinstance(id_token, str):
            raise OidcProviderError("token endpoint não devolveu ID Token")
        return await self.validate_id_token(
            id_token,
            metadata=metadata,
            expected_nonce_digest=expected_nonce_digest,
        )

    async def validate_id_token(
        self,
        id_token: str,
        *,
        metadata: OidcMetadata,
        expected_nonce_digest: str,
    ) -> OidcClaims:
        try:
            header = jwt.get_unverified_header(id_token)
        except InvalidTokenError as error:
            raise OidcProviderError("header do ID Token inválido") from error
        if header.get("alg") != OIDC_ID_TOKEN_ALGORITHM:
            raise OidcProviderError("algoritmo do ID Token não permitido")
        key_id = header.get("kid")
        if not isinstance(key_id, str) or not key_id:
            raise OidcProviderError("ID Token sem kid")
        try:
            jwks_response = await self.client.get(metadata.jwks_uri)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()
        except httpx.HTTPError as error:
            raise OidcProviderError(
                "JWKS do provedor indisponível", unavailable=True
            ) from error
        except ValueError as error:
            raise OidcProviderError("JWKS do provedor inválido") from error
        candidates = [
            key
            for key in jwks.get("keys", [])
            if isinstance(key, dict)
            and key.get("kid") == key_id
            and key.get("kty") == "RSA"
            and key.get("use", "sig") == "sig"
            and key.get("alg", OIDC_ID_TOKEN_ALGORITHM)
            == OIDC_ID_TOKEN_ALGORITHM
        ] if isinstance(jwks, dict) else []
        if len(candidates) != 1:
            raise OidcProviderError("chave de assinatura OIDC não encontrada")
        try:
            signing_key = jwt.PyJWK.from_dict(
                candidates[0], algorithm=OIDC_ID_TOKEN_ALGORITHM
            ).key
            claims = jwt.decode(
                id_token,
                signing_key,
                algorithms=[OIDC_ID_TOKEN_ALGORITHM],
                audience=self.settings.oidc_client_id,
                issuer=metadata.issuer,
                leeway=30,
                options={
                    "require": [
                        "iss",
                        "sub",
                        "aud",
                        "exp",
                        "iat",
                        "nonce",
                    ]
                },
            )
        except (InvalidTokenError, ValueError) as error:
            raise OidcProviderError("ID Token inválido") from error
        nonce = claims.get("nonce")
        if not isinstance(nonce, str) or not hmac.compare_digest(
            digest_secret(nonce), expected_nonce_digest
        ):
            raise OidcProviderError("nonce do ID Token não corresponde")
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject or len(subject) > 255:
            raise OidcProviderError("subject OIDC inválido")
        try:
            subject.encode("ascii")
        except UnicodeEncodeError as error:
            raise OidcProviderError("subject OIDC deve ser ASCII") from error
        audience = claims.get("aud")
        if isinstance(audience, list) and len(audience) > 1:
            if claims.get("azp") != self.settings.oidc_client_id:
                raise OidcProviderError("azp do ID Token inválido")
        email = claims.get("email")
        name = claims.get("name")
        return OidcClaims(
            issuer=metadata.issuer,
            subject=subject,
            email=email if isinstance(email, str) else None,
            email_verified=claims.get("email_verified") is True,
            name=name if isinstance(name, str) else None,
        )
