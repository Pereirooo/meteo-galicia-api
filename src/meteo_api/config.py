from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables (or a .env file)."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="METEO_")

    database_url: str = "sqlite:///./meteo.db"
    meteogalicia_base_url: str = "https://servizos.meteogalicia.gal/mgrss/observacion"
    # MeteoGalicia only keeps the last 72 hours of hourly data.
    ingest_hours: int = 72


settings = Settings()
