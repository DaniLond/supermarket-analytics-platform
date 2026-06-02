"""Servicio de segmentación K-Means."""

import logging
import os
import platform
import subprocess
import sys
from pathlib import Path

import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from app.repositories.segmentation_repo import SegmentationRepository
from app.schemas.segmentation import (
    ClusterProfile,
    ClusterProfilesResponse,
    CustomerClusterResponse,
    ScatterPoint,
    ScatterResponse,
)

logger = logging.getLogger("supermercado.services.segmentation")


def _extract_error(stderr: str, stdout: str) -> str:
    """Filtra barras de progreso de Spark y devuelve el traceback Python real."""
    text = stderr or stdout
    # Buscar último traceback Python
    tb_idx = text.rfind("Traceback (most recent call last)")
    if tb_idx != -1:
        return text[tb_idx:][-3000:]
    # Si no hay traceback, filtrar líneas de progreso de Spark y quedarse con el final
    lines = [
        l for l in text.splitlines()
        if not l.lstrip().startswith("[Stage")
        and "====>" not in l
        and "=====" not in l
    ]
    return "\n".join(lines)[-3000:]


_PCA_FEATURES = ["frequency", "unique_categories", "avg_basket_size", "recency_days"]

_LABEL_POOL = [
    "Frecuente y activo",
    "Comprador regular",
    "Ocasional activo",
    "Fiel pero distante",
    "Inactivo",
    "Nuevo / Esporádico",
    "Explorador",
    "Bajo valor",
]


def _assign_labels(profiles_df: pd.DataFrame) -> dict[int, str]:
    """Rankea clústeres por (frecuencia alta − recencia alta) y asigna etiquetas."""
    def _norm(s: pd.Series) -> pd.Series:
        mn, mx = s.min(), s.max()
        return (s - mn) / (mx - mn + 1e-9)

    # Score: comprar frecuentemente y recientemente es bueno
    scores = _norm(profiles_df["avg_frequency"]) - _norm(profiles_df["avg_recency_days"])
    rank_order = scores.argsort()[::-1].values  # índices de mayor a menor score
    labels: dict[int, str] = {}
    for rank, idx in enumerate(rank_order):
        cid = int(profiles_df.iloc[idx]["cluster_id"])
        labels[cid] = _LABEL_POOL[min(rank, len(_LABEL_POOL) - 1)]
    return labels


class SegmentationService:
    def __init__(self, repo: SegmentationRepository | None = None) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------

    def get_cluster_profiles(self) -> ClusterProfilesResponse:
        assert self._repo is not None
        df = self._repo.cluster_profiles()
        labels = _assign_labels(df)
        profiles = [
            ClusterProfile(
                cluster_id=int(row.cluster_id),
                customer_count=int(row.customer_count),
                avg_frequency=round(float(row.avg_frequency), 2),
                avg_unique_categories=round(float(row.avg_unique_categories), 2),
                avg_basket_size=round(float(row.avg_basket_size), 2),
                avg_recency_days=round(float(row.avg_recency_days), 1),
                label=labels[int(row.cluster_id)],
            )
            for row in df.itertuples()
        ]
        return ClusterProfilesResponse(clusters=sorted(profiles, key=lambda p: p.cluster_id))

    def get_scatter(self, max_points: int = 5_000) -> ScatterResponse:
        assert self._repo is not None
        df = self._repo.all_customers().copy()
        if len(df) > max_points:
            df = df.sample(n=max_points, random_state=42).reset_index(drop=True)
        X = df[_PCA_FEATURES].fillna(0).values
        X_scaled = StandardScaler().fit_transform(X)
        X_pca = PCA(n_components=2, random_state=42).fit_transform(X_scaled)
        points = [
            ScatterPoint(
                customer_id=int(df.iloc[i]["customer_id"]),
                pca_x=round(float(X_pca[i, 0]), 4),
                pca_y=round(float(X_pca[i, 1]), 4),
                cluster=int(df.iloc[i]["cluster"]),
            )
            for i in range(len(df))
        ]
        return ScatterResponse(points=points)

    def get_customer_cluster(self, customer_id: int) -> CustomerClusterResponse | None:
        assert self._repo is not None
        profiles_df = self._repo.cluster_profiles()
        labels = _assign_labels(profiles_df)
        row = self._repo.customer_by_id(customer_id)
        if row is None:
            return None
        cluster_id = int(row["cluster"])
        return CustomerClusterResponse(
            customer_id=customer_id,
            cluster=cluster_id,
            frequency=round(float(row["frequency"]), 2),
            unique_categories=round(float(row["unique_categories"]), 2),
            avg_basket_size=round(float(row["avg_basket_size"]), 2),
            recency_days=round(float(row["recency_days"]), 1),
            label=labels.get(cluster_id, "Desconocido"),
        )

    # ------------------------------------------------------------------
    # Reentrenamiento
    # ------------------------------------------------------------------

    def retrain(self) -> dict:
        from app.core.config import settings
        from app.db import state

        if state.segmentation_training:
            raise RuntimeError("Ya hay un entrenamiento en progreso.")

        logger.info("Disparando reentrenamiento de segmentación K-Means")
        state.segmentation_training = True
        state.segmentation_error = None

        try:
            settings.models_root.mkdir(parents=True, exist_ok=True)
            settings.processed_root.mkdir(parents=True, exist_ok=True)

            script = str(settings.project_root / "spark_jobs" / "train_segmentation.py")
            logger.info("Script: %s | cwd: %s", script, settings.project_root)

            env = os.environ.copy()
            if platform.system() == "Windows":
                import ctypes
                env.setdefault("HADOOP_HOME", str(settings.hadoop_home))

                def _short(path: str) -> str:
                    buf = ctypes.create_unicode_buffer(32768)
                    ret = ctypes.windll.kernel32.GetShortPathNameW(path, buf, len(buf))  # type: ignore[attr-defined]
                    return buf.value if ret else path

                env["PYSPARK_PYTHON"] = _short(sys.executable)
                env["PYSPARK_DRIVER_PYTHON"] = env["PYSPARK_PYTHON"]
                pyspark_dir = str(Path(sys.executable).parent / "Lib" / "site-packages" / "pyspark")
                env["SPARK_HOME"] = _short(pyspark_dir)

            result = subprocess.run(
                [sys.executable, script],
                cwd=str(settings.project_root),
                env=env,
                capture_output=True,
                text=True,
                timeout=600,
            )

            # Siempre loguea la salida completa para facilitar diagnóstico
            if result.stdout:
                logger.info("Spark stdout:\n%s", result.stdout[-3000:])
            if result.stderr:
                logger.warning("Spark stderr:\n%s", result.stderr[-3000:])

            if result.returncode != 0:
                raise RuntimeError(_extract_error(result.stderr, result.stdout))

            clusters_ok = settings.customer_clusters_path.exists()
            rules_ok = settings.association_rules_path.exists()
            state.models_loaded = clusters_ok and rules_ok
            return {"status": "ok", "clusters_ready": clusters_ok, "stdout": result.stdout[-2000:]}

        except Exception:
            state.segmentation_training = False
            raise

        finally:
            state.segmentation_training = False