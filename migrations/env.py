"""Alembic environment: connects migrations to our settings and models."""

import logging

from alembic import context
from sqlalchemy import create_engine, pool

from meteo_api import models  # noqa: F401  (registers the tables on Base.metadata)
from meteo_api.config import settings
from meteo_api.db import Base

logging.basicConfig(format="%(levelname)s [%(name)s] %(message)s")
logging.getLogger("alembic").setLevel(logging.INFO)

# Compared against the database by `alembic revision --autogenerate`.
target_metadata = Base.metadata


def get_url() -> str:
    # Tests can pass a URL through Config.attributes; otherwise use the app settings.
    return context.config.attributes.get("database_url", settings.database_url)


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql`: print the SQL instead of running it."""
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(get_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
