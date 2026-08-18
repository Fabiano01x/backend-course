"""Modelos relacionais usados pela engine assíncrona da Library API."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    MetaData,
    String,
    UniqueConstraint,
    func,
    text,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(column_0_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("btrim(name) <> ''", name="ck_users_name_not_blank"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )
    loans: Mapped[list["Loan"]] = relationship(
        back_populates="user",
        passive_deletes=True,
        lazy="raise",
        order_by="Loan.id",
    )


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        UniqueConstraint("isbn", name="uq_books_isbn"),
        CheckConstraint("btrim(title) <> ''", name="ck_books_title_not_blank"),
        CheckConstraint("btrim(author) <> ''", name="ck_books_author_not_blank"),
        CheckConstraint(
            "char_length(isbn) BETWEEN 10 AND 17",
            name="ck_books_isbn_length",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(), primary_key=True
    )
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(120))
    isbn: Mapped[str] = mapped_column(String(17))
    loans: Mapped[list["Loan"]] = relationship(
        back_populates="book", passive_deletes=True, lazy="raise"
    )


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint(
            "due_at > borrowed_at", name="ck_loans_due_after_borrowed"
        ),
        CheckConstraint(
            "returned_at IS NULL OR returned_at >= borrowed_at",
            name="ck_loans_returned_after_borrowed",
        ),
        Index(
            "uq_loans_one_active_per_book",
            "book_id",
            unique=True,
            postgresql_where=text("returned_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_loans_user", ondelete="RESTRICT")
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", name="fk_loans_book", ondelete="RESTRICT")
    )
    borrowed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="loans", lazy="raise")
    book: Mapped[Book] = relationship(back_populates="loans", lazy="raise")
