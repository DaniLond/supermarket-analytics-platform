"""Endpoint de ingesta"""

import logging
import os
import platform
import subprocess
import sys
from pathlib import Path
from threading import Thread

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import settings
from app.db import state

logger = logging.getLogger("supermercado.api.ingest")
router = APIRouter()

_ingest_status: dict = {"running": False, "last_result": None, "error": None}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class IngestResponse(BaseModel):
    status: str = Field(..., examples=["started"])
    message: str = Field(..., examples=["Job Spark iniciado en background"])


class IngestStatusResponse(BaseModel):
    running: bool = Field(..., examples=[False])
    last_result: str | None = Field(None, examples=["success"])
    error: str | None = Field(None)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _spark_env() -> dict:
    """Construye el entorno para el subproceso Spark."""
    env = os.environ.copy()
    if platform.system() == "Windows":
        env.setdefault("HADOOP_HOME", str(settings.hadoop_home))
        import ctypes

        def _short(path: str) -> str:
            buf = ctypes.create_unicode_buffer(32768)
            ret = ctypes.windll.kernel32.GetShortPathNameW(path, buf, len(buf))
            return buf.value if ret else path

        env["PYSPARK_PYTHON"] = _short(sys.executable)
        env["PYSPARK_DRIVER_PYTHON"] = env["PYSPARK_PYTHON"]
        pyspark_dir = str(Path(sys.executable).parent / "Lib" / "site-packages" / "pyspark")
        env["SPARK_HOME"] = _short(pyspark_dir)
    return env


def _reload_views() -> None:
    """Marca datos como disponibles tras ingesta exitosa."""
    long_path = settings.transactions_long_path
    if not long_path.exists():
        logger.warning("_reload_views: Parquet no encontrado en %s", long_path)
        return
    state.transactions_loaded = True
    logger.info("Datos disponibles — transactions_loaded = True")


def _run_ingest() -> None:
    _ingest_status["running"] = True
    _ingest_status["error"] = None
    script = str(settings.project_root / "spark_jobs" / "ingest_initial_dataset.py")
    try:
        result = subprocess.run(
            [sys.executable, script],
            cwd=str(settings.project_root),
            env=_spark_env(),
            capture_output=True,
            text=True,
            timeout=900,
        )
        if result.returncode == 0:
            _ingest_status["last_result"] = "success"
            _reload_views()
            logger.info("Ingest Spark completado exitosamente")
        else:
            _ingest_status["last_result"] = "failed"
            _ingest_status["error"] = (result.stderr or result.stdout)[-3000:]
            logger.error("Ingest Spark fallido:\n%s", _ingest_status["error"])
    except subprocess.TimeoutExpired:
        _ingest_status["last_result"] = "timeout"
        _ingest_status["error"] = "El job excedio el limite de 15 minutos"
    except Exception as exc:
        _ingest_status["last_result"] = "error"
        _ingest_status["error"] = str(exc)
        logger.exception("Error lanzando Spark: %s", exc)
    finally:
        _ingest_status["running"] = False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=IngestResponse,
    summary="Lanzar pipeline de ingesta Spark",
)
def trigger_ingest() -> IngestResponse:
    """
    Ejecuta spark_jobs/ingest_initial_dataset.py en un hilo de background.
    Lee los CSV de data/DataSet/ y escribe Parquet particionado en data/processed/.
    """
    if _ingest_status["running"]:
        return IngestResponse(
            status="already_running",
            message="El job Spark ya esta en ejecucion",
        )
    Thread(target=_run_ingest, daemon=True).start()
    return IngestResponse(
        status="started",
        message="Job Spark iniciado. Consulta GET /api/v1/ingest/status",
    )


@router.get(
    "/status",
    response_model=IngestStatusResponse,
    summary="Estado del ultimo job de ingesta",
)
def get_status() -> IngestStatusResponse:
    """Devuelve si el job esta corriendo, el resultado del ultimo run y el error si lo hay."""
    return IngestStatusResponse(**_ingest_status)