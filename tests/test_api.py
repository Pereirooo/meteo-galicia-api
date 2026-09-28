def test_health(api):
    assert api.get("/health").json() == {"status": "ok"}


def test_list_stations(api):
    response = api.get("/stations")

    assert response.status_code == 200
    assert [s["name"] for s in response.json()] == ["Coruña-Torre de Hércules", "Mabegondo"]


def test_filter_stations_by_municipality_is_case_insensitive(api):
    response = api.get("/stations", params={"municipality": "abegondo"})

    assert [s["id"] for s in response.json()] == [10045]


def test_get_unknown_station_returns_404(api):
    assert api.get("/stations/1").status_code == 404


def test_observations_filtered_by_parameter_newest_first(api):
    response = api.get("/stations/10157/observations", params={"parameter": "TA_AVG_1.5m"})

    assert response.status_code == 200
    assert [o["value"] for o in response.json()] == [19.0, 17.0]


def test_observations_time_window(api):
    response = api.get(
        "/stations/10157/observations",
        params={"parameter": "TA_AVG_1.5m", "since": "2026-09-28T10:00:00"},
    )

    assert [o["value"] for o in response.json()] == [19.0]


def test_stats(api):
    response = api.get("/stations/10157/stats", params={"parameter": "TA_AVG_1.5m"})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["min"] == 17.0
    assert body["max"] == 19.0
    assert body["mean"] == 18.0
    assert body["unit"] == "ºC"


def test_stats_unknown_parameter_returns_404(api):
    response = api.get("/stations/10157/stats", params={"parameter": "NOPE"})
    assert response.status_code == 404


def test_list_parameters(api):
    codes = [p["code"] for p in api.get("/parameters").json()]
    assert codes == ["PP_SUM_1.5m", "TA_AVG_1.5m"]
