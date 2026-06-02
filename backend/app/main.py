"""
Supermercado Analytics API
"""

import logging
import threading
from contextlib import asynccontextmanager

import duckdb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import setup_logging
from app.db import state

setup_logging()
logger = logging.getLogger("supermercado.api")


# ---------------------------------------------------------------------------
# Background: auto-entrenamiento secuencial (K-Means → FP-Growth)
# Los dos jobs usan Spark; no pueden correr en paralelo.
# ---------------------------------------------------------------------------

def _auto_train_segmentation() -> None:
    from app.services.segmentation_service import SegmentationService
    svc = SegmentationService()
    try:
        result = svc.retrain()
        logger.info("Auto-entrenamiento K-Means completado: clusters_ready=%s", result.get("clusters_ready"))
        state.segmentation_error = None
    except Exception as exc:
        logger.error("Auto-entrenamiento K-Means falló: %s", exc)
        state.segmentation_error = str(exc)[-2000:]
    finally:
        state.segmentation_training = False


def _auto_train_recommendations() -> None:
    from app.services.recommender_service import RecommenderService
    svc = RecommenderService()
    try:
        result = svc.retrain()
        logger.info("Auto-entrenamiento FP-Growth completado: rules_ready=%s", result.get("rules_ready"))
        state.recommendations_error = None
    except Exception as exc:
        logger.error("Auto-entrenamiento FP-Growth falló: %s", exc)
        state.recommendations_error = str(exc)[-2000:]
    finally:
        state.recommendations_training = False


def _auto_train_all_models() -> None:
    """Entrena los modelos que falten, en orden: K-Means primero, luego FP-Growth."""
    if not settings.customer_clusters_path.exists():
        _auto_train_segmentation()
    if not settings.association_rules_path.exists():
        _auto_train_recommendations()


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
            f"SELECT * FROM read_parquet('{long_path.as_posix()}/**/*.parquet', hive_partitioning=true)"
        )
        state.db.execute(
            f"CREATE VIEW transactions_basket AS "
            f"SELECT * FROM read_parquet('{basket_path.as_posix()}/**/*.parquet', hive_partitioning=true)"
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
            f"SELECT * FROM read_parquet('{catalog_path.as_posix()}/*.parquet')"
        )

    rules_path = settings.association_rules_path
    clusters_path = settings.customer_clusters_path
    state.models_loaded = rules_path.exists() and clusters_path.exists()
    logger.info("Modelos cargados: %s", state.models_loaded)

    # Auto-entrenamiento: si faltan modelos, entrenarlos secuencialmente en background
    needs_training = state.transactions_loaded and (
        not clusters_path.exists() or not rules_path.exists()
    )
    if needs_training:
        threading.Thread(target=_auto_train_all_models, daemon=True).start()
        logger.info("Auto-entrenamiento de modelos iniciado en background (K-Means → FP-Growth)")

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
# Routers
# ---------------------------------------------------------------------------
from app.api.v1 import (  # noqa: E402
    analytics,
    ingest,
    recommendations,
    segmentation,
    summary,
    transactions,
)

app.include_router(ingest.router,          prefix="/api/v1/ingest",          tags=["ingest"])
app.include_router(summary.router,         prefix="/api/v1/summary",         tags=["summary"])
app.include_router(analytics.router,       prefix="/api/v1/analytics",       tags=["analytics"])
app.include_router(segmentation.router,    prefix="/api/v1/segmentation",    tags=["segmentation"])
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["recommendations"])
app.include_router(transactions.router,    prefix="/api/v1/transactions",    tags=["transactions"])


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
