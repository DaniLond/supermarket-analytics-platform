"""
Repositorio de segmentación
"""

from pathlib import Path

import pandas as pd


class SegmentationRepository:
    def __init__(self, clusters_path: Path) -> None:
        self._path = clusters_path

    def _load(self) -> pd.DataFrame:
        if not self._path.exists():
            raise FileNotFoundError(
                f"customer_clusters.parquet no encontrado en {self._path}. "
                "Ejecuta POST /api/v1/segmentation/retrain primero."
            )
        return pd.read_parquet(self._path)

    def cluster_profiles(self) -> pd.DataFrame:
        df = self._load()
        return (
            df.groupby("cluster")
            .agg(
                customer_count=("customer_id", "count"),
                avg_frequency=("frequency", "mean"),
                avg_unique_categories=("unique_categories", "mean"),
                avg_basket_size=("avg_basket_size", "mean"),
                avg_recency_days=("recency_days", "mean"),
            )
            .reset_index()
            .rename(columns={"cluster": "cluster_id"})
        )

    def all_customers(self) -> pd.DataFrame:
        return self._load()

    def customer_by_id(self, customer_id: int) -> pd.Series | None:
        df = self._load()
        row = df[df["customer_id"] == customer_id]
        return None if row.empty else row.iloc[0]