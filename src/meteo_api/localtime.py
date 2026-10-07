"""Local calendar days for observations stored in naive UTC.

MeteoGalicia timestamps are UTC, but a "day" in Galicia runs from local midnight to
local midnight, which is UTC+2 in summer and UTC+1 in winter. Grouping by the UTC date
would put the first hours of each day into the previous one.
"""

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import Date, String
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement

from meteo_api.config import settings

TZ = ZoneInfo(settings.timezone)


def day_start_utc(day: date) -> datetime:
    """Local midnight at the start of `day`, as naive UTC (the format stored in the database).

    Filtering with `observed_at >= day_start_utc(a) AND observed_at < day_start_utc(b)`
    compares the raw column, so the database can use its index.
    """
    return datetime.combine(day, time(), TZ).astimezone(UTC).replace(tzinfo=None)


def utc_to_local_date(timestamp: str) -> str:
    """Python implementation of local_date() for SQLite, which has no time zone support."""
    utc = datetime.fromisoformat(timestamp).replace(tzinfo=UTC)
    return utc.astimezone(TZ).date().isoformat()


class local_date(FunctionElement):
    """SQL expression: the local calendar date of a naive-UTC timestamp column."""

    type = Date()
    inherit_cache = True
    name = "local_date"


@compiles(local_date, "postgresql")
def _local_date_postgresql(element, compiler, **kw):
    (column,) = element.clauses
    # Inlined rather than a bound parameter, so the expression is textually identical in
    # SELECT and GROUP BY (PostgreSQL rejects $1 vs $2 as "different" expressions).
    tz = compiler.render_literal_value(settings.timezone, String())
    return f"CAST(timezone({tz}, timezone('UTC', {compiler.process(column, **kw)})) AS DATE)"


@compiles(local_date, "sqlite")
def _local_date_sqlite(element, compiler, **kw):
    # Calls utc_to_local_date(), registered on every SQLite connection in db.py.
    return f"local_date({compiler.process(element.clauses, **kw)})"
