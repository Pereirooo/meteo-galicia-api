from sqlalchemy import func, select

from meteo_api.ingest import ingest
from meteo_api.models import Observation, Parameter, Station


def test_ingest_stores_everything(session, meteogalicia_client):
    result = ingest(session, meteogalicia_client, hours=72)

    assert result == {"stations": 2, "measurements": 4, "inserted": 4}
    assert session.scalar(select(func.count()).select_from(Station)) == 2
    assert session.scalar(select(func.count()).select_from(Parameter)) == 2
    assert session.scalar(select(func.count()).select_from(Observation)) == 4


def test_ingest_is_idempotent(session, meteogalicia_client):
    ingest(session, meteogalicia_client, hours=72)
    second = ingest(session, meteogalicia_client, hours=72)

    assert second["inserted"] == 0
    assert session.scalar(select(func.count()).select_from(Observation)) == 4
