"""Modelos relacionais usados pela engine assíncrona da Library API."""

from datetime import datetime
from uuid import UUID, uuid4

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
    Uuid,
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
    password_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )
    loans: Mapped[list["Loan"]] = relationship(
        back_populates="user",
        passive_deletes=True,
        lazy="raise",
        order_by="Loan.id",
    )
    role_assignments: Mapped[list["UserRole"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
    external_identities: Mapped[list["ExternalIdentity"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="ck_roles_name_not_blank"),
    )

    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    description: Mapped[str] = mapped_column(String(200))
    user_assignments: Mapped[list["UserRole"]] = relationship(
        back_populates="role",
        passive_deletes=True,
        lazy="raise",
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id", name="fk_user_roles_user", ondelete="CASCADE"
        ),
        primary_key=True,
    )
    role_name: Mapped[str] = mapped_column(
        String(40),
        ForeignKey(
            "roles.name", name="fk_user_roles_role", ondelete="RESTRICT"
        ),
        primary_key=True,
    )
    user: Mapped[User] = relationship(
        back_populates="role_assignments", lazy="raise"
    )
    role: Mapped[Role] = relationship(
        back_populates="user_assignments", lazy="raise"
    )


class ExternalIdentity(Base):
    __tablename__ = "external_identities"
    __table_args__ = (
        UniqueConstraint(
            "issuer", "subject", name="uq_external_identities_issuer_subject"
        ),
        CheckConstraint(
            "btrim(issuer) <> ''",
            name="ck_external_identities_issuer_not_blank",
        ),
        CheckConstraint(
            "btrim(subject) <> ''",
            name="ck_external_identities_subject_not_blank",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_external_identities_user",
            ondelete="CASCADE",
        ),
        index=True,
    )
    issuer: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship(
        back_populates="external_identities", lazy="raise"
    )


class OidcLoginAttempt(Base):
    __tablename__ = "oidc_login_attempts"
    __table_args__ = (
        UniqueConstraint(
            "browser_digest", name="uq_oidc_login_attempts_browser_digest"
        ),
        UniqueConstraint(
            "state_digest", name="uq_oidc_login_attempts_state_digest"
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_oidc_login_attempts_expiration_after_creation",
        ),
        CheckConstraint(
            "used_at IS NULL OR used_at >= created_at",
            name="ck_oidc_login_attempts_used_after_creation",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    issuer: Mapped[str] = mapped_column(String(255))
    browser_digest: Mapped[str] = mapped_column(String(64))
    state_digest: Mapped[str] = mapped_column(String(64))
    nonce_digest: Mapped[str] = mapped_column(String(64))
    verifier_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        UniqueConstraint(
            "token_digest", name="uq_refresh_tokens_token_digest"
        ),
        UniqueConstraint(
            "replaced_by_id", name="uq_refresh_tokens_replaced_by_id"
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_refresh_tokens_expiration_after_creation",
        ),
        CheckConstraint(
            "used_at IS NULL OR used_at >= created_at",
            name="ck_refresh_tokens_used_after_creation",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_refresh_tokens_revoked_after_creation",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    family_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_refresh_tokens_user",
            ondelete="RESTRICT",
        ),
        index=True,
    )
    token_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replaced_by_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "refresh_tokens.id",
            name="fk_refresh_tokens_replacement",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
