from fastapi import FastAPI

from meteo_api.routers import parameters, stations

# The database schema is managed by Alembic: run `alembic upgrade head` before starting.
app = FastAPI(
    title="MeteoGalicia API",
    description="Historical weather observations from MeteoGalicia's station network.",
    version="0.1.0",
)
app.include_router(stations.router)
app.include_router(parameters.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
