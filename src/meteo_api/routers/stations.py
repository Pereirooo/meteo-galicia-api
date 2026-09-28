from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from meteo_api.db import get_session
from meteo_api.models import Observation, Parameter, Station
from meteo_api.schemas import ObservationOut, StationOut, StatsOut

router = APIRouter(prefix="/stations", tags=["stations"])

SessionDep = Annotated[Session, Depends(get_session)]


def _get_station_or_404(session: Session, station_id: int) -> Station:
    station = session.get(Station, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    return station


def _get_parameter_or_404(session: Session, code: str) -> Parameter:
    parameter = session.get(Parameter, code)
    if parameter is None:
        raise HTTPException(status_code=404, detail=f"Parameter {code!r} not found")
    return parameter


@router.get("", response_model=list[StationOut])
def list_stations(
    session: SessionDep,
    province: str | None = None,
    municipality: str | None = None,
):
    query = select(Station).order_by(Station.name)
    # Case-insensitive filters: MeteoGalicia stores municipalities in upper case.
    if province:
        query = query.where(func.lower(Station.province) == province.lower())
    if municipality:
        query = query.where(func.lower(Station.municipality) == municipality.lower())
    return session.scalars(query).all()


@router.get("/{station_id}", response_model=StationOut)
def get_station(station_id: int, session: SessionDep):
    return _get_station_or_404(session, station_id)


@router.get("/{station_id}/observations", response_model=list[ObservationOut])
def list_observations(
    station_id: int,
    session: SessionDep,
    parameter: Annotated[str | None, Query(description="e.g. TA_AVG_1.5m")] = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
):
    _get_station_or_404(session, station_id)
    query = select(Observation).where(Observation.station_id == station_id)
    if parameter:
        query = query.where(Observation.parameter_code == parameter)
    if since:
        query = query.where(Observation.observed_at >= since)
    if until:
        query = query.where(Observation.observed_at <= until)
    query = query.order_by(Observation.observed_at.desc(), Observation.parameter_code).limit(limit)
    return session.scalars(query).all()


@router.get("/{station_id}/stats", response_model=StatsOut)
def get_stats(
    station_id: int,
    session: SessionDep,
    parameter: Annotated[str, Query(description="e.g. TA_AVG_1.5m")],
    since: datetime | None = None,
    until: datetime | None = None,
):
    """Aggregate statistics computed in SQL (not in Python) over a time window."""
    _get_station_or_404(session, station_id)
    param = _get_parameter_or_404(session, parameter)

    query = select(
        func.count(Observation.value),
        func.min(Observation.value),
        func.max(Observation.value),
        func.avg(Observation.value),
    ).where(Observation.station_id == station_id, Observation.parameter_code == parameter)
    if since:
        query = query.where(Observation.observed_at >= since)
    if until:
        query = query.where(Observation.observed_at <= until)
    count, min_, max_, mean = session.execute(query).one()

    return StatsOut(
        station_id=station_id,
        parameter_code=parameter,
        unit=param.unit,
        count=count,
        min=min_,
        max=max_,
        mean=round(mean, 2) if mean is not None else None,
        since=since,
        until=until,
    )
