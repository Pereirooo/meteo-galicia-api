"""Response models: the public contract of the API, decoupled from the database tables."""

from datetime import date, datetime
from enum import StrEnum

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


class DailyValue(BaseModel):
    day: date
    count: int  # hourly values in the day: 24 when the station reported every hour
    min: float
    max: float
    mean: float
    sum: float


class DailySummaryOut(BaseModel):
    station_id: int
    parameter_code: str
    unit: str
    timezone: str
    days: list[DailyValue]


class Stat(StrEnum):
    min = "min"
    max = "max"
    mean = "mean"
    sum = "sum"


class RankingEntry(BaseModel):
    rank: int
    station_id: int
    station_name: str
    province: str
    value: float
    count: int


class RankingOut(BaseModel):
    parameter_code: str
    unit: str
    day: date
    stat: Stat
    entries: list[RankingEntry]
