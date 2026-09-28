from contextlib import asynccontextmanager

from fastapi import FastAPI

from meteo_api.db import init_db
from meteo_api.routers import parameters, stations


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="MeteoGalicia API",
    description="Historical weather observations from MeteoGalicia's station network.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(stations.router)
app.include_router(parameters.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
