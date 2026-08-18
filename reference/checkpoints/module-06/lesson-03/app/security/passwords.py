"""Hash e verificação de senhas sem armazenar o valor original."""

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher


password_hash = PasswordHash(
    (
        Argon2Hasher(
            memory_cost=19_456,
            time_cost=2,
            parallelism=1,
        ),
    )
)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return password_hash.verify(password, encoded_hash)
    except UnknownHashError:
        return False


DUMMY_PASSWORD_HASH = hash_password(
    "dummy password used only to equalize authentication work"
)
