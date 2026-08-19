"""Cria identidades de máquina e chaves de API revogáveis."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006_api_keys"
down_revision: str | None = "0005_oidc_identities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_clients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "active", sa.Boolean(), server_default=sa.true(), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''", name="ck_api_clients_name_not_blank"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_api_clients"),
        sa.UniqueConstraint("name", name="uq_api_clients_name"),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("prefix", sa.String(length=12), nullable=False),
        sa.Column("secret_digest", sa.String(length=64), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "char_length(prefix) = 12", name="ck_api_keys_prefix_length"
        ),
        sa.CheckConstraint(
            "char_length(secret_digest) = 64",
            name="ck_api_keys_digest_length",
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at > created_at",
            name="ck_api_keys_expiration_after_creation",
        ),
        sa.CheckConstraint(
            "last_used_at IS NULL OR last_used_at >= created_at",
            name="ck_api_keys_last_use_after_creation",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_api_keys_revoked_after_creation",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["api_clients.id"],
            name="fk_api_keys_client",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_id"],
            ["api_keys.id"],
            name="fk_api_keys_replacement",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_api_keys"),
        sa.UniqueConstraint("prefix", name="uq_api_keys_prefix"),
        sa.UniqueConstraint(
            "replaced_by_id", name="uq_api_keys_replaced_by_id"
        ),
    )
    op.create_index("ix_api_keys_client_id", "api_keys", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_api_keys_client_id", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_table("api_clients")
