"""Cria o esquema relacional inicial da Library API."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_library_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column(
            "active", sa.Boolean(), server_default=sa.true(), nullable=False
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''", name="ck_users_name_not_blank"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "books",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("author", sa.String(length=120), nullable=False),
        sa.Column("isbn", sa.String(length=17), nullable=False),
        sa.CheckConstraint(
            "btrim(author) <> ''", name="ck_books_author_not_blank"
        ),
        sa.CheckConstraint(
            "char_length(isbn) BETWEEN 10 AND 17",
            name="ck_books_isbn_length",
        ),
        sa.CheckConstraint(
            "btrim(title) <> ''", name="ck_books_title_not_blank"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_books"),
        sa.UniqueConstraint("isbn", name="uq_books_isbn"),
    )
    op.create_table(
        "loans",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("book_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "borrowed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "returned_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.CheckConstraint(
            "due_at > borrowed_at", name="ck_loans_due_after_borrowed"
        ),
        sa.CheckConstraint(
            "returned_at IS NULL OR returned_at >= borrowed_at",
            name="ck_loans_returned_after_borrowed",
        ),
        sa.ForeignKeyConstraint(
            ["book_id"], ["books.id"], name="fk_loans_book", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_loans_user", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_loans"),
    )
    op.create_index(
        "uq_loans_one_active_per_book",
        "loans",
        ["book_id"],
        unique=True,
        postgresql_where=sa.text("returned_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_loans_one_active_per_book", table_name="loans")
    op.drop_table("loans")
    op.drop_table("books")
    op.drop_table("users")
