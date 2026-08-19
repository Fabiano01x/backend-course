"""Cria tentativas OIDC e vínculos de identidades externas."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_oidc_identities"
down_revision: str | None = "0004_role_assignments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_identities",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("issuer", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_login_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.CheckConstraint(
            "btrim(issuer) <> ''",
            name="ck_external_identities_issuer_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(subject) <> ''",
            name="ck_external_identities_subject_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_external_identities_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_external_identities"),
        sa.UniqueConstraint(
            "issuer",
            "subject",
            name="uq_external_identities_issuer_subject",
        ),
    )
    op.create_index(
        "ix_external_identities_user_id",
        "external_identities",
        ["user_id"],
    )
    op.create_table(
        "oidc_login_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("issuer", sa.String(length=255), nullable=False),
        sa.Column("browser_digest", sa.String(length=64), nullable=False),
        sa.Column("state_digest", sa.String(length=64), nullable=False),
        sa.Column("nonce_digest", sa.String(length=64), nullable=False),
        sa.Column("verifier_digest", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_oidc_login_attempts_expiration_after_creation",
        ),
        sa.CheckConstraint(
            "used_at IS NULL OR used_at >= created_at",
            name="ck_oidc_login_attempts_used_after_creation",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_oidc_login_attempts"),
        sa.UniqueConstraint(
            "browser_digest",
            name="uq_oidc_login_attempts_browser_digest",
        ),
        sa.UniqueConstraint(
            "state_digest", name="uq_oidc_login_attempts_state_digest"
        ),
    )


def downgrade() -> None:
    op.drop_table("oidc_login_attempts")
    op.drop_index(
        "ix_external_identities_user_id",
        table_name="external_identities",
    )
    op.drop_table("external_identities")
