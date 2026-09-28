"""Thin client for the MeteoGalicia observation API.

It turns MeteoGalicia's JSON (Galician field names, nested lists) into plain dataclasses,
so the rest of the app never depends on the external format.
"""

from dataclasses import dataclass
from datetime import datetime

import httpx

from meteo_api.config import settings


@dataclass(frozen=True)
class StationData:
    id: int
    name: str
    municipality: str
    province: str
    latitude: float
    longitude: float
    altitude: float | None


@dataclass(frozen=True)
class MeasurementData:
    station_id: int
    observed_at: datetime
    parameter_code: str
    parameter_name: str
    unit: str
    value: float
    validation_code: int


class MeteoGaliciaClient:
    def __init__(self, http: httpx.Client | None = None):
        self.http = http or httpx.Client(base_url=settings.meteogalicia_base_url, timeout=30)

    def get_stations(self) -> list[StationData]:
        response = self.http.get("/listaEstacionsMeteo.action")
        response.raise_for_status()
        return [
            StationData(
                id=s["idEstacion"],
                name=s["estacion"],
                municipality=s["concello"],
                province=s["provincia"],
                latitude=s["lat"],
                longitude=s["lon"],
                altitude=s.get("altitude"),
            )
            for s in response.json()["listaEstacionsMeteo"]
        ]

    def get_hourly(self, hours: int, station_id: int | None = None) -> list[MeasurementData]:
        """Hourly measurements for the last `hours` hours (all stations if station_id is None)."""
        params: dict[str, int] = {"numHoras": hours}
        if station_id is not None:
            params["idEst"] = station_id
        response = self.http.get("/ultimosHorariosEstacions.action", params=params)
        response.raise_for_status()

        return [
            MeasurementData(
                station_id=station["idEstacion"],
                observed_at=datetime.fromisoformat(instant["instanteLecturaUTC"]),
                parameter_code=m["codigoParametro"],
                parameter_name=m["nomeParametro"].strip(),
                unit=m["unidade"],
                value=m["valor"],
                validation_code=m["lnCodigoValidacion"],
            )
            for station in response.json()["listHorarios"]
            for instant in station["listaInstantes"]
            for m in instant["listaMedidas"]
        ]
