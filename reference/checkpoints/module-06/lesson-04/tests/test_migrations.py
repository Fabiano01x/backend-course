from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


PROJECT = Path(__file__).resolve().parents[1]


def alembic_config() -> Config:
    config = Config(PROJECT / "alembic.ini")
    config.set_main_option("script_location", str(PROJECT / "alembic"))
    return config


def test_revision_history_has_one_auditable_head() -> None:
    scripts = ScriptDirectory.from_config(alembic_config())
    head = scripts.get_current_head()
    revision = scripts.get_revision(head)

    assert head == "0004_role_assignments"
    assert revision is not None
    assert revision.down_revision == "0003_refresh_token_rotation"
    assert revision.doc == "Cria o catálogo de papéis e as atribuições de usuários."


def test_upgrade_and_downgrade_can_be_rendered_without_database() -> None:
    upgrade_sql = StringIO()
    upgrade_config = alembic_config()
    upgrade_config.output_buffer = upgrade_sql
    command.upgrade(upgrade_config, "head", sql=True)

    downgrade_sql = StringIO()
    downgrade_config = alembic_config()
    downgrade_config.output_buffer = downgrade_sql
    command.downgrade(downgrade_config, "head:base", sql=True)

    rendered_upgrade = upgrade_sql.getvalue()
    rendered_downgrade = downgrade_sql.getvalue()
    assert "CREATE TABLE users" in rendered_upgrade
    assert "CREATE TABLE books" in rendered_upgrade
    assert "CREATE TABLE loans" in rendered_upgrade
    assert "CREATE UNIQUE INDEX uq_loans_one_active_per_book" in rendered_upgrade
    assert "ADD COLUMN password_hash VARCHAR(255)" in rendered_upgrade
    assert "CREATE TABLE refresh_tokens" in rendered_upgrade
    assert "CREATE INDEX ix_refresh_tokens_family_id" in rendered_upgrade
    assert "CREATE TABLE roles" in rendered_upgrade
    assert "CREATE TABLE user_roles" in rendered_upgrade
    assert "INSERT INTO user_roles" in rendered_upgrade
    assert "DROP TABLE user_roles" in rendered_downgrade
    assert "DROP TABLE roles" in rendered_downgrade
    assert "DROP TABLE refresh_tokens" in rendered_downgrade
    assert "DROP COLUMN password_hash" in rendered_downgrade
    assert "DROP TABLE loans" in rendered_downgrade
    assert "DROP TABLE books" in rendered_downgrade
    assert "DROP TABLE users" in rendered_downgrade


def test_configuration_keeps_credentials_out_of_alembic_ini() -> None:
    ini = (PROJECT / "alembic.ini").read_text(encoding="utf-8")
    environment = (PROJECT / "alembic" / "env.py").read_text(encoding="utf-8")

    assert "sqlalchemy.url" not in ini
    assert "target_metadata = Base.metadata" in environment
    assert "build_database_url(Settings())" in environment
