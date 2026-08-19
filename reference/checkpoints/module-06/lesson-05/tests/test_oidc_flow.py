from datetime import UTC, datetime
from urllib.parse import parse_qs, urlencode, urlsplit

from httpx import AsyncClient
import pytest

from app.config import Settings
from app.dependencies import get_oidc_provider, get_settings
from app.integrations.oidc import OidcClaims
from app.main import app
from app.models import (
    ExternalIdentity,
    OidcLoginAttempt,
    RefreshToken,
    User,
)
from app.security.oidc import (
    OIDC_ATTEMPT_COOKIE,
    digest_secret,
    parse_attempt_cookie,
)
from app.security.tokens import decode_access_token
from app.services.oidc import (
    OidcFlowError,
    consume_oidc_attempt,
    resolve_external_identity,
)
from tests.support import RecordingSession, Result


pytestmark = pytest.mark.anyio
ISSUER = "https://idp.example"


def oidc_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        oidc_issuer=ISSUER,
        oidc_client_id="library-web",
        oidc_client_secret="external-client-secret",
        oidc_redirect_uri="http://test/auth/oidc/callback",
    )


class FakeProvider:
    def __init__(self, claims: OidcClaims | None = None) -> None:
        self.claims = claims or OidcClaims(
            issuer=ISSUER,
            subject="subject-123",
            email="ADA@EXAMPLE.COM",
            email_verified=True,
            name="Ada Lovelace",
        )
        self.authorization: dict[str, str] = {}
        self.exchanges: list[dict[str, str]] = []

    async def authorization_url(
        self, *, state: str, nonce: str, code_challenge: str
    ) -> str:
        self.authorization = {
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
        }
        return f"{ISSUER}/authorize?{urlencode(self.authorization)}"

    async def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
        expected_nonce_digest: str,
    ) -> OidcClaims:
        self.exchanges.append(
            {
                "code": code,
                "code_verifier": code_verifier,
                "expected_nonce_digest": expected_nonce_digest,
            }
        )
        return self.claims


def configure_oidc(provider: FakeProvider) -> Settings:
    settings = oidc_settings()

    async def override_settings() -> Settings:
        return settings

    async def override_provider() -> FakeProvider:
        return provider

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_oidc_provider] = override_provider
    return settings


async def start_flow(
    client: AsyncClient, provider: FakeProvider
) -> tuple[object, str]:
    response = await client.get("/auth/oidc/login")
    assert response.status_code == 307
    query = parse_qs(urlsplit(response.headers["location"]).query)
    return response, query["state"][0]


async def test_start_binds_state_nonce_and_pkce_to_httponly_cookie(
    client: AsyncClient, session: RecordingSession
) -> None:
    provider = FakeProvider()
    settings = configure_oidc(provider)

    response, state = await start_flow(client, provider)

    attempt = session.added[0]
    assert isinstance(attempt, OidcLoginAttempt)
    assert session.commit_count == 1
    assert attempt.issuer == ISSUER
    assert attempt.state_digest == digest_secret(state)
    assert state not in {
        attempt.browser_digest,
        attempt.state_digest,
        attempt.nonce_digest,
        attempt.verifier_digest,
    }
    raw_cookie = response.cookies[OIDC_ATTEMPT_COOKIE]
    parsed_cookie = parse_attempt_cookie(raw_cookie)
    assert parsed_cookie is not None
    browser_secret, verifier = parsed_cookie
    assert attempt.browser_digest == digest_secret(browser_secret)
    assert attempt.verifier_digest == digest_secret(verifier)
    assert provider.authorization["code_challenge"] != verifier
    set_cookie = response.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/auth/oidc" in set_cookie
    assert "Secure" not in set_cookie
    assert settings.oidc_attempt_expire_minutes == 10


async def test_callback_creates_external_member_and_local_session(
    client: AsyncClient, session: RecordingSession
) -> None:
    provider = FakeProvider()
    settings = configure_oidc(provider)
    start_response, state = await start_flow(client, provider)
    attempt = session.added[0]
    session.execute_results.extend(
        [
            Result(scalars=[attempt]),
            Result(rows=[]),
            Result(),
        ]
    )

    callback = await client.get(
        "/auth/oidc/callback",
        params={"code": "authorization-code", "state": state},
    )

    assert callback.status_code == 200
    claims = decode_access_token(callback.json()["access_token"], settings)
    assert claims.user_id == 1
    parsed_cookie = parse_attempt_cookie(
        start_response.cookies[OIDC_ATTEMPT_COOKIE]
    )
    assert parsed_cookie is not None
    assert provider.exchanges == [
        {
            "code": "authorization-code",
            "code_verifier": parsed_cookie[1],
            "expected_nonce_digest": attempt.nonce_digest,
        }
    ]
    created_user = next(item for item in session.added if isinstance(item, User))
    identity = next(
        item for item in session.added if isinstance(item, ExternalIdentity)
    )
    refresh = next(
        item for item in session.added if isinstance(item, RefreshToken)
    )
    assert created_user.email == "ada@example.com"
    assert created_user.password_hash is None
    assert [role.role_name for role in created_user.role_assignments] == ["member"]
    assert identity.issuer == ISSUER
    assert identity.subject == "subject-123"
    assert identity.user is created_user
    assert refresh.user_id == created_user.id
    cookies = callback.headers.get_list("set-cookie")
    assert any("library_refresh=" in cookie for cookie in cookies)
    assert any(
        f"{OIDC_ATTEMPT_COOKIE}=" in cookie and "Max-Age=0" in cookie
        for cookie in cookies
    )


async def test_existing_email_is_not_automatically_linked(
    client: AsyncClient, session: RecordingSession
) -> None:
    provider = FakeProvider()
    configure_oidc(provider)
    _, state = await start_flow(client, provider)
    attempt = session.added[0]
    local_user = User(
        id=7,
        name="Local User",
        email="ada@example.com",
        active=True,
    )
    session.execute_results.extend(
        [
            Result(scalars=[attempt]),
            Result(rows=[]),
            Result(scalars=[local_user]),
        ]
    )

    callback = await client.get(
        "/auth/oidc/callback",
        params={"code": "authorization-code", "state": state},
    )

    assert callback.status_code == 409
    assert callback.json() == {
        "detail": "E-mail já pertence a uma conta local"
    }
    assert not any(
        isinstance(item, ExternalIdentity) for item in session.added
    )


async def test_consumed_attempt_cannot_be_replayed(
    client: AsyncClient, session: RecordingSession
) -> None:
    provider = FakeProvider()
    configure_oidc(provider)
    response, state = await start_flow(client, provider)
    attempt = session.added[0]
    raw_cookie = response.cookies[OIDC_ATTEMPT_COOKIE]
    session.execute_results.append(Result(scalars=[attempt]))

    consumed = await consume_oidc_attempt(
        session,
        raw_cookie=raw_cookie,
        state=state,
        issuer=ISSUER,
        now=datetime.now(UTC),
    )
    session.execute_results.append(Result(scalars=[attempt]))

    with pytest.raises(OidcFlowError, match="inválida"):
        await consume_oidc_attempt(
            session,
            raw_cookie=raw_cookie,
            state=state,
            issuer=ISSUER,
            now=datetime.now(UTC),
        )

    assert consumed.code_verifier == parse_attempt_cookie(raw_cookie)[1]


async def test_existing_link_uses_issuer_and_subject_not_current_email(
    session: RecordingSession,
) -> None:
    user = User(
        id=42,
        name="Linked User",
        email="old-address@example.com",
        active=True,
    )
    identity = ExternalIdentity(
        id=9,
        user_id=42,
        issuer=ISSUER,
        subject="subject-123",
        last_login_at=datetime.now(UTC),
    )
    session.execute_results.append(Result(rows=[(identity, user)]))
    claims = OidcClaims(
        issuer=ISSUER,
        subject="subject-123",
        email="new-address@example.com",
        email_verified=False,
        name="Changed Name",
    )

    user_id = await resolve_external_identity(session, claims)

    assert user_id == 42
    assert user.email == "old-address@example.com"
    assert identity.user_id == 42
    assert session.flush_count == 1


async def test_new_identity_requires_verified_email(
    session: RecordingSession,
) -> None:
    session.execute_results.append(Result(rows=[]))
    claims = OidcClaims(
        issuer=ISSUER,
        subject="subject-without-email",
        email="unverified@example.com",
        email_verified=False,
        name="Unverified",
    )

    with pytest.raises(OidcFlowError, match="não confirmou"):
        await resolve_external_identity(session, claims)

    assert not any(isinstance(item, User) for item in session.added)
