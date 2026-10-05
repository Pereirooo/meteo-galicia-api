from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

PYPROJECT = Path(__file__).parents[1] / "pyproject.toml"


@pytest.fixture
def alembic_config(db_engine) -> Config:
    config = Config(toml_file=PYPROJECT)
    config.attributes["database_url"] = db_engine.url.render_as_string(hide_password=False)
    return config


def test_upgrade_creates_all_tables(alembic_config, db_engine):
    command.upgrade(alembic_config, "head")

    tables = set(inspect(db_engine).get_table_names())
    assert {"stations", "parameters", "observations"} <= tables


def test_models_and_migrations_are_in_sync(alembic_config):
    # Fails if someone changes models.py without generating a migration.
    command.upgrade(alembic_config, "head")
    command.check(alembic_config)


def test_downgrade_to_empty_database(alembic_config, db_engine):
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")

    assert inspect(db_engine).get_table_names() == ["alembic_version"]
