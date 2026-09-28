from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from meteo_api.db import Base


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # MeteoGalicia's idEstacion
    name: Mapped[str] = mapped_column(String(100))
    municipality: Mapped[str] = mapped_column(String(100), index=True)
    province: Mapped[str] = mapped_column(String(50), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    altitude: Mapped[float | None] = mapped_column(Float)


class Parameter(Base):
    """A measured variable, e.g. TA_AVG_1.5m = average air temperature at 1.5 m."""

    __tablename__ = "parameters"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    unit: Mapped[str] = mapped_column(String(30))


class Observation(Base):
    """One hourly value of one parameter at one station (long/"tidy" format)."""

    __tablename__ = "observations"
    __table_args__ = (
        # Makes ingestion idempotent: re-ingesting the same hour is a no-op.
        UniqueConstraint("station_id", "observed_at", "parameter_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), index=True)
    parameter_code: Mapped[str] = mapped_column(ForeignKey("parameters.code"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, index=True)  # naive UTC
    value: Mapped[float] = mapped_column(Float)
    validation_code: Mapped[int] = mapped_column(Integer)
