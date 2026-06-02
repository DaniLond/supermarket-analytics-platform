"""Servicio de recomendaciones FP-Growth."""

import logging
import os
import platform
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd

from app.repositories.recommendations_repo import RecommendationsRepository
from app.schemas.recommendations import (
    AssociationRuleOut,
    CategoryRecommendationsResponse,
    CustomerRecommendationsResponse,
    ProductInfo,
    ProductsByCategoryResponse,
)

logger = logging.getLogger("supermercado.services.recommender")


def _extract_error(stderr: str, stdout: str) -> str:
    text = stderr or stdout
    tb_idx = text.rfind("Traceback (most recent call last)")
    if tb_idx != -1:
        return text[tb_idx:][-3000:]
    lines = [
        l for l in text.splitlines()
        if not l.lstrip().startswith("[Stage")
        and "====>" not in l
        and "=====" not in l
    ]
    return "\n".join(lines)[-3000:]


def _row_to_rule(row) -> AssociationRuleOut:
    return AssociationRuleOut(
        antecedent=list(row.antecedent),
        consequent=list(row.consequent),
        support=round(float(row.support), 4),
        confidence=round(float(row.confidence), 4),
        lift=round(float(row.lift), 4),
    )


class RecommenderService:
    def __init__(self, repo: RecommendationsRepository | None = None) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def get_rules_for_category(self, category_id: int) -> CategoryRecommendationsResponse:
        assert self._repo is not None
        df = self._repo.rules_for_category(category_id)
        rules = [_row_to_rule(row) for row in df.itertuples()]
        return CategoryRecommendationsResponse(category_id=category_id, rules=rules)

    def get_rules_for_customer(
        self, customer_id: int, db: duckdb.DuckDBPyConnection
    ) -> CustomerRecommendationsResponse:
        assert self._repo is not None

        recent_df = db.execute(
            "SELECT DISTINCT category_id FROM transactions_long WHERE customer_id = ?",
            [customer_id],
        ).df()
        recent_categories: list[int] = recent_df["category_id"].tolist()

        cluster: int | None = None
        from app.core.config import settings
        if settings.customer_clusters_path.exists():
            cdf = pd.read_parquet(settings.customer_clusters_path)
            row = cdf[cdf["customer_id"] == customer_id]
            if not row.empty:
                cluster = int(row.iloc[0]["cluster"])

        rules_df = self._repo.rules_for_customer(recent_categories)
        bought_set = set(recent_categories)
        recommended: set[int] = set()
        for row in rules_df.itertuples():
            for cat in row.consequent:
                if cat not in bought_set:
                    recommended.add(cat)

        rules = [_row_to_rule(row) for row in rules_df.itertuples()]
        return CustomerRecommendationsResponse(
            customer_id=customer_id,
            cluster=cluster,
            recommended_categories=sorted(recommended),
            rules_used=rules,
        )

    def get_products_by_category(
        self, category_id: int, db: duckdb.DuckDBPyConnection
    ) -> ProductsByCategoryResponse:
        products_df = db.execute(
            "SELECT product_code, category_id FROM catalog WHERE category_id = ? LIMIT 50",
            [category_id],
        ).df()
        products = [
            ProductInfo(
                product_code=int(row.product_code),
                category_id=int(row.category_id),
            )
            for row in products_df.itertuples()
        ]
        return ProductsByCategoryResponse(category_id=category_id, products=products)

    # ------------------------------------------------------------------
    # Reentrenamiento
    # ------------------------------------------------------------------

    def retrain(self) -> dict:
        from app.core.config import settings
        from app.db import state

        logger.info("Disparando reentrenamiento FP-Growth")

        settings.models_root.mkdir(parents=True, exist_ok=True)

        script = str(settings.project_root / "spark_jobs" / "train_recommender.py")
        logger.info("Script: %s | cwd: %s", script, settings.project_root)

        env = os.environ.copy()
        if platform.system() == "Windows":
            import ctypes

            env.setdefault("HADOOP_HOME", str(settings.hadoop_home))

            def _short(path: str) -> str:
                buf = ctypes.create_unicode_buffer(32768)
                ret = ctypes.windll.kernel32.GetShortPathNameW(path, buf, len(buf))
                return buf.value if ret else path

            env["PYSPARK_PYTHON"] = _short(sys.executable)
            env["PYSPARK_DRIVER_PYTHON"] = env["PYSPARK_PYTHON"]
            pyspark_dir = str(
                Path(sys.executable).parent / "Lib" / "site-packages" / "pyspark"
            )
            env["SPARK_HOME"] = _short(pyspark_dir)

        result = subprocess.run(
            [sys.executable, script],
            cwd=str(settings.project_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.stdout:
            logger.info("FP-Growth stdout:\n%s", result.stdout[-3000:])
        if result.stderr:
            logger.warning("FP-Growth stderr:\n%s", result.stderr[-3000:])

        if result.returncode != 0:
            raise RuntimeError(_extract_error(result.stderr, result.stdout))

        rules_ok = settings.association_rules_path.exists()
        state.models_loaded = rules_ok and settings.customer_clusters_path.exists()
        return {"status": "ok", "rules_ready": rules_ok, "stdout": result.stdout[-2000:]}