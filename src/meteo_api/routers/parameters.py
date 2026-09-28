from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from meteo_api.db import get_session
from meteo_api.models import Parameter
from meteo_api.schemas import ParameterOut

router = APIRouter(prefix="/parameters", tags=["parameters"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[ParameterOut])
def list_parameters(session: SessionDep):
    return session.scalars(select(Parameter).order_by(Parameter.code)).all()
