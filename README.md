# MeteoGalicia API

![CI](https://github.com/Pereirooo/meteo-galicia-api/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)

REST API that collects and serves **historical weather observations** from the ~150 automatic stations of [MeteoGalicia](https://www.meteogalicia.gal/), Galicia's public weather service.

## Why

MeteoGalicia publishes live station data as open data, but its API only keeps the **last 72 hours**. This project runs a periodic ingestion job that accumulates those observations in a database, and exposes them through an API with filtering and aggregated statistics, so you can ask questions like *"what was the average temperature in A Coruña last week?"*.

## Architecture

```
MeteoGalicia API ──► ingest job ──► database ──► FastAPI ──► clients
 (JSON, 72 h)        (hourly,       (stations,    (REST + OpenAPI docs)
                      idempotent)    parameters,
                                     observations)
```

- **`meteogalicia.py`**: HTTP client that translates MeteoGalicia's JSON (Galician field names, nested lists) into plain dataclasses, isolating the rest of the app from the external format.
- **`ingest.py`**: downloads stations and hourly measurements and stores them. Observations have a unique constraint on `(station, time, parameter)` and are inserted with `ON CONFLICT DO NOTHING`, so the job can run as often as needed without creating duplicates.
- **`models.py`**: observations are stored in *long* format (one row per station/time/parameter), so new parameters don't require schema changes.
- **`migrations/`**: the schema is versioned with [Alembic](https://alembic.sqlalchemy.org/). A test checks that migrations and models never drift apart.
- **`routers/`**: API endpoints. Statistics are computed in SQL, not in Python.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stations?province=&municipality=` | List stations (case-insensitive filters) |
| GET | `/stations/{id}` | Station details |
| GET | `/stations/{id}/observations?parameter=&since=&until=&limit=` | Observations, newest first |
| GET | `/stations/{id}/stats?parameter=&since=&until=` | Count, min, max and mean over a time window |
| GET | `/parameters` | Measured variables (code, name, unit) |
| GET | `/health` | Health check |

Interactive documentation is available at `/docs` once the server is running.

Example:

```bash
curl "localhost:8000/stations/10157/stats?parameter=TA_AVG_1.5m"
```
```json
{"station_id":10157,"parameter_code":"TA_AVG_1.5m","unit":"ºC","count":72,
 "min":14.95,"max":21.49,"mean":18.25,"since":null,"until":null}
```

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

alembic upgrade head            # create/update the database schema
meteo-ingest                    # download the last 72 h into ./meteo.db
uvicorn meteo_api.main:app --reload
```

Configuration is done through environment variables (or a `.env` file):

| Variable | Default |
|----------|---------|
| `METEO_DATABASE_URL` | `sqlite:///./meteo.db` |
| `METEO_INGEST_HOURS` | `72` |

## Development

```bash
pytest                          # tests (no network: MeteoGalicia is mocked)
ruff check . && ruff format .   # lint + format
```

Changing the schema:

```bash
# 1. edit src/meteo_api/models.py
alembic revision --autogenerate -m "describe the change"   # 2. generate a migration
# 3. review the file in migrations/versions/
alembic upgrade head                                        # 4. apply it
```

CI runs lint and tests on every push and pull request.

## Roadmap

- [x] Ingestion of stations and hourly observations
- [x] REST API with filters and statistics
- [x] Tests and CI
- [x] Schema migrations with Alembic
- [ ] PostgreSQL
- [ ] Docker Compose (API + database + scheduled ingestion)
- [ ] Daily aggregates and rankings (e.g. rainiest station of the month)
- [ ] Deployment

## Data source

Data from [MeteoGalicia](https://www.meteogalicia.gal/) (Xunta de Galicia), published as open data.
