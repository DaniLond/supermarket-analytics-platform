"""Repositorio del catálogo de productos y categorías."""

import logging

import duckdb
import pandas as pd

logger = logging.getLogger("supermercado.repos.catalog")


class CatalogRepository:
    def __init__(self, db: duckdb.DuckDBPyConnection) -> None:
        self._db = db

    def all_categories(self) -> pd.DataFrame:
        return self._db.execute(
            "SELECT DISTINCT category_id, category_name FROM transactions_long ORDER BY category_id"
        ).df()

    def products_by_category(self, category_id: int, limit: int = 20) -> pd.DataFrame:
        return self._db.execute(
            "SELECT * FROM catalog WHERE category_id = ? LIMIT ?",
            [category_id, limit],
        ).df()
