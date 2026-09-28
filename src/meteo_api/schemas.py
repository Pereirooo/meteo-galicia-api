"""Response models: the public contract of the API, decoupled from the database tables."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    municipality: str
    province: str
    latitude: float
    longitude: float
    altitude: float | None


class ParameterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    unit: str


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    observed_at: datetime
    parameter_code: str
    value: float


class StatsOut(BaseModel):
    station_id: int
    parameter_code: str
    unit: str
    count: int
    min: float | None
    max: float | None
    mean: float | None
    since: datetime | None
    until: datetime | None
