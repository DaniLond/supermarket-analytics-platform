"""Endpoints de ingesta de transacciones nuevas y re-entrenamiento de modelos."""

import logging
import threading

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.v1.models import NewTransaction, TransactionBatch
from app.core.config import settings
from app.db import state
from app.services.ingestion_service import IngestionService

logger = logging.getLogger("supermercado.api.transactions")
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas de respuesta
# ---------------------------------------------------------------------------

class IngestResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    transactions_ingested: int = Field(..., examples=[5])
    retrain_triggered: bool = Field(..., examples=[True])
    message: str = Field(..., examples=["Datos añadidos. Re-entrenamiento iniciado en background."])


class PipelineStatusResponse(BaseModel):
    transactions_loaded: bool
    last_ingest_count: int
    last_ingest_error: str | None
    segmentation_training: bool
    segmentation_error: str | None
    recommendations_training: bool
    recommendations_error: str | None
    models_ready: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trigger_retrain(force: bool = True) -> None:
    """Lanza re-entrenamiento completo en hilo background."""
    from app.main import _auto_train_all_models

    if state.segmentation_training or state.recommendations_training:
        logger.info("Reentrenamiento ya en progreso — se omite disparo duplicado")
        return
    # Marcar como en progreso antes de arrancar el hilo para cerrar la ventana de carrera
    state.segmentation_training = True
    state.recommendations_training = True
    threading.Thread(target=_auto_train_all_models, args=(force,), daemon=True).start()
    logger.info("Re-entrenamiento K-Means + FP-Growth disparado en background")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=IngestResponse,
    status_code=202,
    summary="Ingestar nuevas transacciones y re-entrenar modelos automáticamente",
)
def ingest_transactions(body: TransactionBatch) -> IngestResponse:
    """
    Recibe un lote de transacciones, las agrega al Parquet procesado y dispara
    el re-entrenamiento de K-Means y FP-Growth en background.
    """
    svc = IngestionService(
        long_path=settings.transactions_long_path,
        basket_path=settings.transactions_basket_path,
        catalog_path=settings.catalog_path,
    )

    try:
        txs = [t.model_dump() for t in body.transactions]
        count = svc.ingest(txs)
    except Exception as exc:
        state.last_ingest_error = str(exc)
        logger.error("Error en ingesta: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error al escribir los datos: {exc}")

    state.last_ingest_count = count
    state.last_ingest_error = None
    state.transactions_loaded = True

    _trigger_retrain(force=True)

    return IngestResponse(
        status="ok",
        transactions_ingested=count,
        retrain_triggered=True,
        message=(
            f"{count} transacción(es) añadida(s). "
            "Re-entrenamiento de modelos iniciado en background — "
            "consulta GET /api/v1/transactions/status para seguimiento."
        ),
    )


@router.post(
    "/retrain",
    status_code=202,
    summary="Forzar re-entrenamiento de todos los modelos",
)
def force_retrain() -> dict:
    """Dispara re-entrenamiento de K-Means y FP-Growth aunque ya existan modelos."""
    if state.segmentation_training or state.recommendations_training:
        raise HTTPException(
            status_code=409,
            detail="Ya hay un entrenamiento en progreso. Espera a que termine.",
        )
    _trigger_retrain(force=True)
    return {"status": "started", "message": "Re-entrenamiento iniciado en background."}


@router.get(
    "/status",
    response_model=PipelineStatusResponse,
    summary="Estado del pipeline: ingesta + entrenamiento de modelos",
)
def pipeline_status() -> PipelineStatusResponse:
    """Devuelve el estado completo del pipeline de datos y modelos."""
    return PipelineStatusResponse(
        transactions_loaded=state.transactions_loaded,
        last_ingest_count=state.last_ingest_count,
        last_ingest_error=state.last_ingest_error,
        segmentation_training=state.segmentation_training,
        segmentation_error=state.segmentation_error,
        recommendations_training=state.recommendations_training,
        recommendations_error=state.recommendations_error,
        models_ready=(
            settings.customer_clusters_path.exists()
            and settings.association_rules_path.exists()
        ),
    )