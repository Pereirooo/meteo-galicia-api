"""Download data from MeteoGalicia and store it in the database.

Run it periodically (e.g. every hour) to build up a history beyond MeteoGalicia's 72-hour window:

    meteo-ingest                # last 72 hours, all stations
    meteo-ingest --hours 3
    meteo-ingest --every 3600   # keep running, once per hour
"""

import argparse
import logging
import time

from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from meteo_api.config import settings
from meteo_api.db import SessionLocal
from meteo_api.meteogalicia import MeteoGaliciaClient
from meteo_api.models import Observation, Parameter, Station

logger = logging.getLogger(__name__)


def _insert_ignoring_duplicates(session: Session, model, rows: list[dict]) -> int:
    """INSERT ... ON CONFLICT DO NOTHING (SQLite and PostgreSQL). Returns rows inserted."""
    if not rows:
        return 0
    dialects = {"postgresql": postgresql.insert, "sqlite": sqlite.insert}
    dialect = session.get_bind().dialect.name
    if dialect not in dialects:
        raise NotImplementedError(f"Unsupported database: {dialect}")
    # RETURNING only yields the rows actually inserted, so we can count them.
    stmt = dialects[dialect](model).on_conflict_do_nothing().returning(model.id)
    return len(session.execute(stmt, rows).all())


def ingest(session: Session, client: MeteoGaliciaClient, hours: int) -> dict[str, int]:
    stations = client.get_stations()
    for s in stations:
        # merge = upsert by primary key, so station metadata stays up to date.
        session.merge(Station(**vars(s)))

    measurements = client.get_hourly(hours)
    known_station_ids = {s.id for s in stations}
    measurements = [m for m in measurements if m.station_id in known_station_ids]

    parameters = {m.parameter_code: (m.parameter_name, m.unit) for m in measurements}
    for code, (name, unit) in parameters.items():
        session.merge(Parameter(code=code, name=name, unit=unit))
    session.flush()

    inserted = _insert_ignoring_duplicates(
        session,
        Observation,
        [
            {
                "station_id": m.station_id,
                "parameter_code": m.parameter_code,
                "observed_at": m.observed_at,
                "value": m.value,
                "validation_code": m.validation_code,
            }
            for m in measurements
        ],
    )
    session.commit()
    return {"stations": len(stations), "measurements": len(measurements), "inserted": inserted}


def run_once(hours: int) -> None:
    with SessionLocal() as session:
        result = ingest(session, MeteoGaliciaClient(), hours)
    logger.info(
        "Stations: %(stations)d · measurements fetched: %(measurements)d · new rows: %(inserted)d",
        result,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hours", type=int, default=settings.ingest_hours)
    parser.add_argument(
        "--every", type=int, metavar="SECONDS", help="keep running, ingesting every SECONDS"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.every is None:
        run_once(args.hours)
        return

    while True:
        try:
            run_once(args.hours)
        except Exception:
            # A failed run (e.g. MeteoGalicia is down) must not stop the scheduler;
            # the next run re-downloads the whole window, so nothing is lost.
            logger.exception("Ingestion failed; retrying in %d s", args.every)
        time.sleep(args.every)


if __name__ == "__main__":
    main()
