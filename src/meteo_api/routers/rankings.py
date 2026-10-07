from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from meteo_api.localtime import TZ, day_start_utc
from meteo_api.models import Observation, Station
from meteo_api.routers.deps import SessionDep, get_parameter_or_404
from meteo_api.schemas import RankingEntry, RankingOut, Stat

router = APIRouter(prefix="/rankings", tags=["rankings"])

AGGREGATES = {Stat.min: func.min, Stat.max: func.max, Stat.mean: func.avg, Stat.sum: func.sum}


@router.get("", response_model=RankingOut)
def get_ranking(
    session: SessionDep,
    parameter: Annotated[str, Query(description="e.g. PP_SUM_1.5m")],
    day: Annotated[date | None, Query(description="Local day (default: yesterday)")] = None,
    stat: Stat = Stat.mean,
    order: Literal["desc", "asc"] = "desc",
    limit: Annotated[int, Query(ge=1, le=200)] = 10,
    by_province: bool = False,
):
    """Stations ranked by a statistic over one local day.

    For example, the rainiest stations (`parameter=PP_SUM_1.5m&stat=sum`) or the coldest
    (`parameter=TA_AVG_1.5m&stat=min&order=asc`). With `by_province=true` the ranking is
    computed within each province. Tied stations share a rank, so there may be more than
    `limit` entries.
    """
    param = get_parameter_or_404(session, parameter)
    if day is None:
        day = datetime.now(TZ).date() - timedelta(days=1)  # the last complete day

    value = AGGREGATES[stat](Observation.value)
    # Window function: numbers the grouped rows (one per station) without collapsing them,
    # restarting at 1 in every province when partitioned.
    rank = func.rank().over(
        partition_by=Station.province if by_province else None,
        order_by=value.desc() if order == "desc" else value.asc(),
    )
    ranked = (
        select(
            rank.label("rank"),
            Station.id.label("station_id"),
            Station.name.label("station_name"),
            Station.province,
            value.label("value"),
            func.count(Observation.value).label("count"),
        )
        .select_from(Observation)
        .join(Station, Station.id == Observation.station_id)
        .where(
            Observation.parameter_code == parameter,
            Observation.observed_at >= day_start_utc(day),
            Observation.observed_at < day_start_utc(day + timedelta(days=1)),
        )
        .group_by(Station.id, Station.name, Station.province)
        .subquery()
    )
    # A window function can't be filtered in its own WHERE, hence the subquery.
    query = (
        select(ranked)
        .where(ranked.c.rank <= limit)
        .order_by(
            *([ranked.c.province] if by_province else []), ranked.c.rank, ranked.c.station_name
        )
    )

    return RankingOut(
        parameter_code=parameter,
        unit=param.unit,
        day=day,
        stat=stat,
        entries=[
            RankingEntry(**{**row, "value": round(row["value"], 2)})
            for row in session.execute(query).mappings()
        ],
    )
