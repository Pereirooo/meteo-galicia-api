from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from meteo_api.config import settings
from meteo_api.localtime import day_start_utc, local_date
from meteo_api.models import Observation, Station
from meteo_api.routers.deps import SessionDep, get_parameter_or_404, get_station_or_404
from meteo_api.schemas import DailySummaryOut, DailyValue, ObservationOut, StationOut, StatsOut

router = APIRouter(prefix="/stations", tags=["stations"])


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
    return get_station_or_404(session, station_id)


@router.get("/{station_id}/observations", response_model=list[ObservationOut])
def list_observations(
    station_id: int,
    session: SessionDep,
    parameter: Annotated[str | None, Query(description="e.g. TA_AVG_1.5m")] = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
):
    get_station_or_404(session, station_id)
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
    get_station_or_404(session, station_id)
    param = get_parameter_or_404(session, parameter)

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


@router.get("/{station_id}/daily", response_model=DailySummaryOut)
def get_daily_summary(
    station_id: int,
    session: SessionDep,
    parameter: Annotated[str, Query(description="e.g. TA_AVG_1.5m")],
    start: Annotated[date | None, Query(description="First local day (inclusive)")] = None,
    end: Annotated[date | None, Query(description="Last local day (inclusive)")] = None,
):
    """Statistics per local calendar day (midnight to midnight in Galicia, not UTC).

    Use `sum` for accumulated quantities such as rainfall and `min`/`max`/`mean` for
    instantaneous ones such as temperature.
    """
    get_station_or_404(session, station_id)
    param = get_parameter_or_404(session, parameter)
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start must not be after end")

    day = local_date(Observation.observed_at)
    query = (
        select(
            day.label("day"),
            func.count(Observation.value).label("count"),
            func.min(Observation.value).label("min"),
            func.max(Observation.value).label("max"),
            func.avg(Observation.value).label("mean"),
            func.sum(Observation.value).label("sum"),
        )
        .where(Observation.station_id == station_id, Observation.parameter_code == parameter)
        .group_by(day)
        .order_by(day)
    )
    if start:
        query = query.where(Observation.observed_at >= day_start_utc(start))
    if end:
        query = query.where(Observation.observed_at < day_start_utc(end + timedelta(days=1)))

    return DailySummaryOut(
        station_id=station_id,
        parameter_code=parameter,
        unit=param.unit,
        timezone=settings.timezone,
        days=[
            DailyValue(**{**row, "mean": round(row["mean"], 2), "sum": round(row["sum"], 2)})
            for row in session.execute(query).mappings()
        ],
    )
