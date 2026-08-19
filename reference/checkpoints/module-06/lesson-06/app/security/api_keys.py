"""Geração e verificação de credenciais opacas para clientes de máquina."""

from dataclasses import dataclass
import hashlib
import re
import secrets


API_KEY_PATTERN = re.compile(
    r"\Alka_(?P<prefix>[0-9a-f]{12})_(?P<secret>[A-Za-z0-9_-]{43})\Z"
)


@dataclass(frozen=True, slots=True)
class GeneratedApiKey:
    raw: str
    prefix: str
    digest: str


def digest_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("ascii", errors="strict")).hexdigest()


def generate_api_key() -> GeneratedApiKey:
    prefix = secrets.token_hex(6)
    secret = secrets.token_urlsafe(32)
    raw = f"lka_{prefix}_{secret}"
    return GeneratedApiKey(raw=raw, prefix=prefix, digest=digest_api_key(raw))


def api_key_prefix(raw: str) -> str | None:
    match = API_KEY_PATTERN.fullmatch(raw)
    return match.group("prefix") if match else None


def matches_api_key(raw: str, expected_digest: str) -> bool:
    try:
        candidate_digest = digest_api_key(raw)
    except UnicodeEncodeError:
        candidate_digest = "0" * 64
    return secrets.compare_digest(candidate_digest, expected_digest)
