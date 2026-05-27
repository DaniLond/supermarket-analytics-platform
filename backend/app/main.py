"""
Supermercado Analytics API
==========================
Backend principal de la plataforma de analítica de transacciones de supermercado.

Arquitectura:
    Ingesta (Spark) → Parquet particionado → DuckDB (API) → FastAPI → React

Patrón heredado del Lab 10: lifespan, Pydantic v2 con Field+examples, ErrorResponse,
logging estructurado, CORS abierto para desarrollo.
"""

import logging
from contextlib import asynccontextmanager

import duckdb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger("supermercado.api")


# ---------------------------------------------------------------------------
# Estado global compartido (inyectado desde lifespan)
# ---------------------------------------------------------------------------
class AppState:
    db: duckdb.DuckDBPyConnection | None = None
    transactions_loaded: bool = False
    models_loaded: bool = False


state = AppState()


# ---------------------------------------------------------------------------
# Lifespan — inicializa DuckDB y registra vistas sobre Parquet
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando Supermercado Analytics API v%s", settings.app_version)

    # Conexión DuckDB en memoria; las vistas apuntan a los Parquet procesados
    state.db = duckdb.connect(":memory:")

    long_path = settings.transactions_long_path
    basket_path = settings.transactions_basket_path
    catalog_path = settings.catalog_path

    if long_path.exists():
        state.db.execute(
            f"CREATE VIEW transactions_long AS "
            f"SELECT * FROM read_parquet('{long_path}/**/*.parquet', hive_partitioning=true)"
        )
        state.db.execute(
            f"CREATE VIEW transactions_basket AS "
            f"SELECT * FROM read_parquet('{basket_path}/**/*.parquet', hive_partitioning=true)"
        )
        state.transactions_loaded = True
        count = state.db.execute("SELECT COUNT(*) FROM transactions_long").fetchone()[0]
        logger.info("Transacciones (long) cargadas: %d filas", count)
    else:
        logger.warning(
            "Parquet no encontrado en %s. Ejecuta spark_jobs/ingest_initial_dataset.py primero.",
            long_path,
        )

    if catalog_path.exists():
        state.db.execute(
            f"CREATE VIEW catalog AS "
            f"SELECT * FROM read_parquet('{catalog_path}/*.parquet')"
        )

    rules_path = settings.association_rules_path
    clusters_path = settings.customer_clusters_path
    state.models_loaded = rules_path.exists() and clusters_path.exists()
    logger.info("Modelos cargados: %s", state.models_loaded)

    yield

    if state.db:
        state.db.close()
    logger.info("API apagada.")


# ---------------------------------------------------------------------------
# Schemas base reutilizables
# ---------------------------------------------------------------------------
class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
    transactions_loaded: bool
    models_loaded: bool
    version: str


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "API REST para analítica descriptiva, diagnóstica y avanzada de transacciones "
        "de supermercado. Procesamiento batch con PySpark, almacén Parquet + DuckDB."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers (se agregan en secciones posteriores)
# ---------------------------------------------------------------------------
# from app.api.v1 import summary, analytics, segmentation, recommendations, transactions
# app.include_router(summary.router, prefix="/api/v1/summary", tags=["summary"])
# app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
# app.include_router(segmentation.router, prefix="/api/v1/segmentation", tags=["segmentation"])
# app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["recommendations"])
# app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])


# ---------------------------------------------------------------------------
# Endpoints base
# ---------------------------------------------------------------------------
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["meta"],
    summary="Health check",
    responses={500: {"model": ErrorResponse}},
)
def health() -> HealthResponse:
    """Verifica que la API esté activa y reporta el estado de datos y modelos."""
    return HealthResponse(
        status="ok",
        transactions_loaded=state.transactions_loaded,
        models_loaded=state.models_loaded,
        version=settings.app_version,
    )
