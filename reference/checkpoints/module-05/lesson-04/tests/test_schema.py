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
