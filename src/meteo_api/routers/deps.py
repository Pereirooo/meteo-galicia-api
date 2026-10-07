"""Dependencies and lookups shared by several routers."""

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from meteo_api.db import get_session
from meteo_api.models import Parameter, Station

SessionDep = Annotated[Session, Depends(get_session)]


def get_station_or_404(session: Session, station_id: int) -> Station:
    station = session.get(Station, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    return station


def get_parameter_or_404(session: Session, code: str) -> Parameter:
    parameter = session.get(Parameter, code)
    if parameter is None:
        raise HTTPException(status_code=404, detail=f"Parameter {code!r} not found")
    return parameter
