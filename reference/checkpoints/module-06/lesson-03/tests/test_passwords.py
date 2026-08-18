from app.security.passwords import hash_password, verify_password


def test_argon2id_hashes_are_salted_and_verifiable() -> None:
    password = "correct horse battery staple"
    first = hash_password(password)
    second = hash_password(password)

    assert first.startswith("$argon2id$")
    assert "m=19456,t=2,p=1" in first
    assert second.startswith("$argon2id$")
    assert first != second
    assert password not in first
    assert verify_password(password, first) is True
    assert verify_password("wrong password", first) is False


def test_unknown_hash_format_is_rejected_without_exception() -> None:
    assert verify_password("candidate", "not-a-supported-hash") is False
