# ---- Build stage: install the app and its dependencies ----
FROM python:3.13-slim AS builder

WORKDIR /build

# Dependencies first, with an empty package: this layer is cached and only rebuilt
# when pyproject.toml changes, not on every code change.
COPY pyproject.toml README.md ./
RUN mkdir -p src/meteo_api && touch src/meteo_api/__init__.py \
    && pip install --no-cache-dir --prefix=/install .

# Now the real code (cheap to rebuild: dependencies are already installed).
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install --no-deps .


# ---- Runtime stage: only what is needed to run ----
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    METEO_DATABASE_URL=sqlite:////app/data/meteo.db

COPY --from=builder /install /usr/local

WORKDIR /app
# Alembic reads its config from pyproject.toml and needs the migration scripts.
COPY pyproject.toml ./
COPY migrations ./migrations

# Don't run as root.
RUN useradd --create-home app && mkdir data && chown app data
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "meteo_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
