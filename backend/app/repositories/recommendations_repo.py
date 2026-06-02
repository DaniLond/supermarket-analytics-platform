"""Repositorio de reglas de asociación FP-Growth."""

from pathlib import Path

import pandas as pd


class RecommendationsRepository:
    def __init__(self, rules_path: Path) -> None:
        self._path = rules_path
        self._rules: pd.DataFrame | None = None

    def _load(self) -> pd.DataFrame:
        if self._rules is None:
            if not self._path.exists():
                raise FileNotFoundError(
                    f"association_rules.parquet no encontrado en {self._path}."
                )
            self._rules = pd.read_parquet(self._path)
        return self._rules

    def rules_for_category(self, category_id: int, limit: int = 10) -> pd.DataFrame:
        """Reglas cuyo antecedente contiene category_id, ordenadas por lift."""
        df = self._load()
        mask = df["antecedent"].apply(lambda x: category_id in x)
        return df[mask].sort_values("lift", ascending=False).head(limit)

    def rules_for_customer(
        self, recent_categories: list[int], limit: int = 10
    ) -> pd.DataFrame:
        """Reglas cuyo antecedente es subconjunto de las categorías recientes del cliente."""
        df = self._load()
        recent_set = set(recent_categories)
        mask = df["antecedent"].apply(
            lambda x: len(x) > 0 and set(x).issubset(recent_set)
        )
        return df[mask].sort_values("lift", ascending=False).head(limit)

    def top_rules(self, limit: int = 20) -> pd.DataFrame:
        """Reglas globales con mayor lift."""
        df = self._load()
        return df.sort_values("lift", ascending=False).head(limit)