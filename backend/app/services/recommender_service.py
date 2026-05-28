"""Servicio de recomendaciones FP-Growth."""

import logging
import subprocess
from pathlib import Path

import pandas as pd

logger = logging.getLogger("supermercado.services.recommender")


class RecommenderService:
    def __init__(self, rules_path: Path) -> None:
        self._rules_path = rules_path
        self._rules: pd.DataFrame | None = None

    def load(self) -> None:
        if self._rules_path.exists():
            self._rules = pd.read_parquet(self._rules_path)
            logger.info("Reglas de asociación cargadas: %d reglas", len(self._rules))

    def retrain(self) -> dict:
        logger.info("Disparando reentrenamiento del recomendador FP-Growth")
        result = subprocess.run(
            ["python", "spark_jobs/train_recommender.py"],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Spark job falló:\n{result.stderr}")
        self.load()
        return {"status": "ok", "stdout": result.stdout[-2000:]}
