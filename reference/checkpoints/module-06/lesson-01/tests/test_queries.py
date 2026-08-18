from sqlalchemy.dialects import postgresql

from app.routers.books import build_book_queries


def postgres_sql(statement: object) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).lower()


def test_book_page_translates_filter_count_order_and_slice_to_sql() -> None:
    count_statement, page_statement = build_book_queries(
        available=False,
        author="50%_Books",
        sort_by="title",
        order="desc",
        limit=10,
        offset=20,
    )

    count_sql = postgres_sql(count_statement)
    page_sql = postgres_sql(page_statement)
    compiled_count = count_statement.compile(dialect=postgresql.dialect())

    assert "count(books.id)" in count_sql
    assert "exists (select loans.id" in count_sql
    assert "loans.returned_at is null" in count_sql
    assert "books.author ilike" in count_sql
    assert "escape" in count_sql
    assert "%50\\%\\_Books%" in compiled_count.params.values()
    assert "order by" not in count_sql
    assert "limit" not in count_sql
    assert "not (exists (select loans.id" in page_sql
    assert "as available" in page_sql
    assert "order by lower(books.title) desc, books.id desc" in page_sql
    assert "limit 10 offset 20" in page_sql


def test_available_filter_uses_not_exists_and_id_order_is_not_duplicated() -> None:
    count_statement, page_statement = build_book_queries(
        available=True,
        author=None,
        sort_by="id",
        order="asc",
        limit=20,
        offset=0,
    )

    count_sql = postgres_sql(count_statement)
    page_sql = postgres_sql(page_statement)

    assert "not (exists (select loans.id" in count_sql
    assert page_sql.count("books.id asc") == 1
    assert "limit 20 offset 0" in page_sql
