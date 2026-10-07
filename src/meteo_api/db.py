import sqlite3
from collections.abc import Iterator

from sqlalchemy import Engine, MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from meteo_api.config import settings
from meteo_api.localtime import utc_to_local_date


class Base(DeclarativeBase):
    # Deterministic constraint names, so future migrations can refer to (and drop) them.
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


@event.listens_for(Engine, "connect")
def _register_sqlite_functions(dbapi_connection, connection_record):
    # Runs for every new connection of any engine (including the tests' ones).
    if isinstance(dbapi_connection, sqlite3.Connection):
        dbapi_connection.create_function("local_date", 1, utc_to_local_date, deterministic=True)


engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    with SessionLocal() as session:
        yield session
