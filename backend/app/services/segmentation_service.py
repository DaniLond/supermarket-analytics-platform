"""Servicio de segmentación K-Means."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("supermercado.services.segmentation")


class SegmentationService:
    def __init__(self, clusters_path: Path, kmeans_model_path: Path) -> None:
        self._clusters_path = clusters_path
        self._kmeans_model_path = kmeans_model_path

    def retrain(self) -> dict:
        """Dispara el job Spark de segmentación en un subproceso."""
        logger.info("Disparando reentrenamiento de segmentación K-Means")
        result = subprocess.run(
            ["python", "spark_jobs/train_segmentation.py"],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Spark job falló:\n{result.stderr}")
        return {"status": "ok", "stdout": result.stdout[-2000:]}
