from datetime import datetime


def test_get_stations_maps_fields(meteogalicia_client):
    stations = meteogalicia_client.get_stations()

    assert len(stations) == 2
    torre = stations[0]
    assert torre.id == 10157
    assert torre.name == "Coruña-Torre de Hércules"
    assert torre.municipality == "A CORUÑA"
    assert torre.province == "A Coruña"


def test_get_hourly_flattens_measurements(meteogalicia_client):
    measurements = meteogalicia_client.get_hourly(hours=2)

    # 2 instants x 2 parameters; the station without data contributes nothing.
    assert len(measurements) == 4
    first = measurements[0]
    assert first.station_id == 10157
    assert first.observed_at == datetime(2026, 9, 28, 10, 0)
    assert first.parameter_code == "TA_AVG_1.5m"
    assert first.value == 19.0


def test_parameter_names_are_stripped(meteogalicia_client):
    names = {m.parameter_name for m in meteogalicia_client.get_hourly(hours=2)}
    assert all(name == name.strip() for name in names)
