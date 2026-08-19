"""Cria o catálogo de papéis e as atribuições de usuários."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004_role_assignments"
down_revision: str | None = "0003_refresh_token_rotation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    roles = op.create_table(
        "roles",
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.CheckConstraint(
            "btrim(name) <> ''", name="ck_roles_name_not_blank"
        ),
        sa.PrimaryKeyConstraint("name", name="pk_roles"),
    )
    op.bulk_insert(
        roles,
        [
            {
                "name": "member",
                "description": "Retira livros e consulta o próprio histórico.",
            },
            {
                "name": "librarian",
                "description": "Administra acervo, usuários e devoluções.",
            },
        ],
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role_name", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_name"],
            ["roles.name"],
            name="fk_user_roles_role",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_roles_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "user_id", "role_name", name="pk_user_roles"
        ),
    )
    op.execute(
        sa.text(
            "INSERT INTO user_roles (user_id, role_name) "
            "SELECT id, 'member' FROM users"
        )
    )


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("roles")
