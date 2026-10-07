from fastapi import APIRouter
from sqlalchemy import select

from meteo_api.models import Parameter
from meteo_api.routers.deps import SessionDep
from meteo_api.schemas import ParameterOut

router = APIRouter(prefix="/parameters", tags=["parameters"])


@router.get("", response_model=list[ParameterOut])
def list_parameters(session: SessionDep):
    return session.scalars(select(Parameter).order_by(Parameter.code)).all()
