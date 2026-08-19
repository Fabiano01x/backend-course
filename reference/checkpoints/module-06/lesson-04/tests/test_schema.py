import re
from pathlib import Path


SCHEMA = Path(__file__).resolve().parents[1] / "schema.sql"


def schema_text() -> str:
    return SCHEMA.read_text(encoding="utf-8").lower()


def table_body(sql: str, table: str) -> str:
    match = re.search(rf"create table {table} \((.*?)\n\);", sql, re.DOTALL)
    assert match is not None
    return match.group(1)


def test_declares_library_entities_and_referential_integrity() -> None:
    sql = schema_text()

    assert "create table users" in sql
    assert "create table books" in sql
    assert "create table loans" in sql
    assert "create table refresh_tokens" in sql
    assert "create table roles" in sql
    assert "create table user_roles" in sql
    assert "foreign key (user_id) references users (id) on delete restrict" in sql
    assert "foreign key (book_id) references books (id) on delete restrict" in sql


def test_keeps_derived_availability_out_of_books() -> None:
    sql = schema_text()

    assert "available" not in table_body(sql, "books")
    assert "where returned_at is null" in sql
    assert "unique index uq_loans_one_active_per_book" in sql


def test_enforces_identity_and_temporal_rules() -> None:
    sql = schema_text()

    assert "constraint uq_users_email unique (email)" in sql
    assert "constraint uq_books_isbn unique (isbn)" in sql
    assert "check (due_at > borrowed_at)" in sql
    assert "returned_at is null or returned_at >= borrowed_at" in sql


def test_password_hash_is_optional_for_preexisting_users() -> None:
    users = table_body(schema_text(), "users")

    assert "password_hash varchar(255)" in users
    assert "password_hash varchar(255) not null" not in users
    assert "password " not in users


def test_refresh_tokens_store_only_digest_and_rotation_state() -> None:
    refresh_tokens = table_body(schema_text(), "refresh_tokens")

    assert "token_digest varchar(64) not null" in refresh_tokens
    assert "family_id uuid not null" in refresh_tokens
    assert "used_at timestamptz" in refresh_tokens
    assert "revoked_at timestamptz" in refresh_tokens
    assert "replaced_by_id uuid" in refresh_tokens
    assert "refresh_token " not in refresh_tokens
    assert "token_value" not in refresh_tokens


def test_role_assignments_are_normalized_and_referentially_protected() -> None:
    roles = table_body(schema_text(), "roles")
    assignments = table_body(schema_text(), "user_roles")

    assert "name varchar(40) primary key" in roles
    assert "primary key (user_id, role_name)" in assignments
    assert "references users (id) on delete cascade" in assignments
    assert "references roles (name) on delete restrict" in assignments
    assert "('member', 'retira livros" in schema_text()
    assert "select id, 'member' from users" in schema_text()
