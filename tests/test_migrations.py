from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

PYPROJECT = Path(__file__).parents[1] / "pyproject.toml"


@pytest.fixture
def alembic_config(tmp_path) -> Config:
    config = Config(toml_file=PYPROJECT)
    config.attributes["database_url"] = f"sqlite:///{tmp_path / 'test.db'}"
    return config


def test_upgrade_creates_all_tables(alembic_config):
    command.upgrade(alembic_config, "head")

    engine = create_engine(alembic_config.attributes["database_url"])
    tables = set(inspect(engine).get_table_names())
    assert {"stations", "parameters", "observations"} <= tables


def test_models_and_migrations_are_in_sync(alembic_config):
    # Fails if someone changes models.py without generating a migration.
    command.upgrade(alembic_config, "head")
    command.check(alembic_config)


def test_downgrade_to_empty_database(alembic_config):
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")

    engine = create_engine(alembic_config.attributes["database_url"])
    assert inspect(engine).get_table_names() == ["alembic_version"]
