from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from meteo_api.db import get_session
from meteo_api.main import app
from meteo_api.models import Observation, Parameter, Station

TEMP, RAIN = "TA_AVG_1.5m", "PP_SUM_1.5m"
CORUNA, MABEGONDO, LUGO = 10157, 10045, 10111

# Galicia is UTC+2 until 25 October 2026 and UTC+1 afterwards: in October, 22:00 UTC is
# already midnight of the next local day; in December it is still 23:00 of the same day.
OBSERVATIONS = [
    (CORUNA, TEMP, "2026-10-05T21:00", 10.0),  # 23:00 on 5 October
    (CORUNA, TEMP, "2026-10-05T22:00", 20.0),  # 00:00 on 6 October
    (CORUNA, TEMP, "2026-10-06T12:00", 30.0),
    (CORUNA, TEMP, "2026-12-01T22:00", 5.0),  # 23:00 on 1 December (winter time)
    (CORUNA, RAIN, "2026-10-05T21:00", 100.0),  # 5 October: not part of 6 October's ranking
    (CORUNA, RAIN, "2026-10-05T22:00", 2.0),
    (CORUNA, RAIN, "2026-10-06T10:00", 3.0),
    (MABEGONDO, RAIN, "2026-10-06T10:00", 2.0),
    (MABEGONDO, RAIN, "2026-10-06T11:00", 2.0),  # same daily total as Lugo
    (LUGO, RAIN, "2026-10-06T10:00", 4.0),
]


@pytest.fixture
def api(session) -> TestClient:
    session.add_all(
        [
            Station(id=CORUNA, name="Coruña-Torre de Hércules", municipality="A CORUÑA",
                    province="A Coruña", latitude=43.38, longitude=-8.41, altitude=21),
            Station(id=MABEGONDO, name="Mabegondo", municipality="ABEGONDO",
                    province="A Coruña", latitude=43.24, longitude=-8.26, altitude=94),
            Station(id=LUGO, name="Lugo-Campus", municipality="LUGO",
                    province="Lugo", latitude=43.0, longitude=-7.55, altitude=400),
            Parameter(code=TEMP, name="Temperatura media a 1.5m", unit="ºC"),
            Parameter(code=RAIN, name="Chuvia", unit="L/m2"),
        ]
    )  # fmt: skip
    session.flush()
    session.add_all(
        Observation(
            station_id=station,
            parameter_code=parameter,
            observed_at=datetime.fromisoformat(at),
            value=value,
            validation_code=1,
        )
        for station, parameter, at, value in OBSERVATIONS
    )
    session.commit()

    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_daily_summary_uses_local_days(api):
    response = api.get(f"/stations/{CORUNA}/daily", params={"parameter": TEMP})

    assert response.status_code == 200
    body = response.json()
    assert body["unit"] == "ºC"
    assert body["timezone"] == "Europe/Madrid"
    assert body["days"] == [
        {"day": "2026-10-05", "count": 1, "min": 10.0, "max": 10.0, "mean": 10.0, "sum": 10.0},
        {"day": "2026-10-06", "count": 2, "min": 20.0, "max": 30.0, "mean": 25.0, "sum": 50.0},
        # Winter time: 22:00 UTC is still 1 December, not 2 December.
        {"day": "2026-12-01", "count": 1, "min": 5.0, "max": 5.0, "mean": 5.0, "sum": 5.0},
    ]


def test_daily_summary_date_range_is_in_local_days(api):
    response = api.get(
        f"/stations/{CORUNA}/daily",
        params={"parameter": TEMP, "start": "2026-10-06", "end": "2026-10-06"},
    )

    # Includes the reading at 22:00 UTC on 5 October (local midnight on the 6th).
    assert [(d["day"], d["count"]) for d in response.json()["days"]] == [("2026-10-06", 2)]


def test_daily_summary_rejects_inverted_range(api):
    response = api.get(
        f"/stations/{CORUNA}/daily",
        params={"parameter": TEMP, "start": "2026-10-07", "end": "2026-10-06"},
    )

    assert response.status_code == 422


def test_daily_summary_unknown_parameter_returns_404(api):
    response = api.get(f"/stations/{CORUNA}/daily", params={"parameter": "NOPE"})

    assert response.status_code == 404


def _ranking(api, **params) -> list[tuple[str, float]]:
    response = api.get("/rankings", params={"parameter": RAIN, "day": "2026-10-06", **params})
    assert response.status_code == 200
    return [(e["station_name"], e["value"]) for e in response.json()["entries"]]


def test_ranking_rainiest_stations_of_a_day(api):
    # Coruña's 100 L/m2 fell on 5 October (local time), so it doesn't count.
    # Lugo and Mabegondo tie for second place, so both are included.
    assert _ranking(api, stat="sum", limit=2) == [
        ("Coruña-Torre de Hércules", 5.0),
        ("Lugo-Campus", 4.0),
        ("Mabegondo", 4.0),
    ]


def test_ranking_ascending(api):
    assert _ranking(api, stat="max", order="asc", limit=1) == [("Mabegondo", 2.0)]


def test_ranking_by_province(api):
    response = api.get(
        "/rankings",
        params={"parameter": RAIN, "day": "2026-10-06", "stat": "sum", "by_province": True,
                "limit": 1},
    )  # fmt: skip

    assert [(e["province"], e["rank"], e["station_id"]) for e in response.json()["entries"]] == [
        ("A Coruña", 1, CORUNA),
        ("Lugo", 1, LUGO),
    ]


def test_ranking_rejects_unknown_stat(api):
    response = api.get("/rankings", params={"parameter": RAIN, "stat": "median"})

    assert response.status_code == 422
