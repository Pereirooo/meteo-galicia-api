import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from meteo_api import models  # noqa: F401  (registers the tables)
from meteo_api.db import Base, get_session
from meteo_api.ingest import ingest
from meteo_api.main import app
from meteo_api.meteogalicia import MeteoGaliciaClient

# Trimmed-down copies of real MeteoGalicia responses.
STATIONS_JSON = {
    "idTipo": None,
    "listaEstacionsMeteo": [
        {
            "altitude": 21.0,
            "concello": "A CORUÑA",
            "estacion": "Coruña-Torre de Hércules",
            "idEstacion": 10157,
            "lat": 43.382763,
            "lon": -8.409202,
            "provincia": "A Coruña",
        },
        {
            "altitude": 94.0,
            "concello": "ABEGONDO",
            "estacion": "Mabegondo",
            "idEstacion": 10045,
            "lat": 43.241367,
            "lon": -8.262225,
            "provincia": "A Coruña",
        },
    ],
}


def _measure(code: str, name: str, unit: str, value: float) -> dict:
    return {
        "codigoParametro": code,
        "lnCodigoValidacion": 1,
        "nomeParametro": name,
        "unidade": unit,
        "valor": value,
    }


HOURLY_JSON = {
    "listHorarios": [
        {
            "estacion": "Coruña-Torre de Hércules",
            "idEstacion": 10157,
            "listaInstantes": [
                {
                    "instanteLecturaUTC": "2026-09-28T10:00:00",
                    "listaMedidas": [
                        _measure("TA_AVG_1.5m", "Temperatura  a 1.5m", "ºC", 19.0),
                        _measure("PP_SUM_1.5m", "Chuvia", "L/m2", 0.0),
                    ],
                },
                {
                    "instanteLecturaUTC": "2026-09-28T09:00:00",
                    "listaMedidas": [
                        _measure("TA_AVG_1.5m", "Temperatura  a 1.5m", "ºC", 17.0),
                        _measure("PP_SUM_1.5m", "Chuvia", "L/m2", 1.2),
                    ],
                },
            ],
        },
        # Stations with no data come back with an empty list.
        {"estacion": "Mabegondo", "idEstacion": 10045, "listaInstantes": []},
    ]
}


def _fake_meteogalicia(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/listaEstacionsMeteo.action"):
        return httpx.Response(200, json=STATIONS_JSON)
    if request.url.path.endswith("/ultimosHorariosEstacions.action"):
        return httpx.Response(200, json=HOURLY_JSON)
    return httpx.Response(404)


@pytest.fixture
def meteogalicia_client() -> MeteoGaliciaClient:
    http = httpx.Client(
        base_url="https://test/mgrss/observacion", transport=httpx.MockTransport(_fake_meteogalicia)
    )
    return MeteoGaliciaClient(http)


@pytest.fixture
def session() -> Session:
    # In-memory SQLite shared across threads (TestClient runs the app in another thread).
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


@pytest.fixture
def populated_session(session, meteogalicia_client) -> Session:
    ingest(session, meteogalicia_client, hours=72)
    return session


@pytest.fixture
def api(populated_session) -> TestClient:
    app.dependency_overrides[get_session] = lambda: populated_session
    yield TestClient(app)
    app.dependency_overrides.clear()
