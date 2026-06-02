"""Servicio de ingesta de transacciones nuevas vía API."""

import hashlib
import logging
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger("supermercado.services.ingestion")


def _row_hash(date_: date, store_id: int, customer_id: int) -> str:
    key = f"{date_}|{store_id}|{customer_id}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _load_cat_names(catalog_path: Path) -> dict[int, str]:
    """Carga el mapa category_id → category_name desde el catálogo Parquet."""
    if not catalog_path.exists():
        return {}
    try:
        df = pd.read_parquet(catalog_path)
        if "category_id" in df.columns and "category_name" in df.columns:
            return dict(zip(df["category_id"].astype(int), df["category_name"].astype(str)))
    except Exception:
        pass
    return {}


class IngestionService:
    def __init__(self, long_path: Path, basket_path: Path, catalog_path: Path | None = None) -> None:
        self._long_path = long_path
        self._basket_path = basket_path
        self._catalog_path = catalog_path

    def ingest(self, transactions: list[dict]) -> int:
        """Persiste nuevas transacciones en Parquet particionado."""
        cat_names: dict[int, str] = {}
        if self._catalog_path:
            cat_names = _load_cat_names(self._catalog_path)

        rows_long: list[dict] = []
        rows_basket: list[dict] = []

        for tx in transactions:
            date_ = tx["date"]
            store_id = int(tx["store_id"])
            customer_id = int(tx["customer_id"])
            categories: list[int] = [int(c) for c in tx["categories"]]
            tx_id = _row_hash(date_, store_id, customer_id)
            year_month = date_.strftime("%Y-%m") if hasattr(date_, "strftime") else str(date_)[:7]

            rows_basket.append({
                "transaction_id": tx_id,
                "date": str(date_),
                "store_id": store_id,
                "customer_id": customer_id,
                "categories": categories,
                "basket_size": len(categories),
                "year_month": year_month,
            })
            for cat in categories:
                rows_long.append({
                    "transaction_id": tx_id,
                    "date": str(date_),
                    "store_id": store_id,
                    "customer_id": customer_id,
                    "category_id": cat,
                    "category_name": cat_names.get(cat, f"Cat {cat}"),
                    "year_month": year_month,
                })

        if rows_long:
            self._write_parquet(pd.DataFrame(rows_long), self._long_path)
            self._write_parquet(pd.DataFrame(rows_basket), self._basket_path)
            logger.info(
                "Ingestadas %d transacciones / %d líneas long",
                len(transactions), len(rows_long),
            )

        return len(transactions)

    def _write_parquet(self, df: pd.DataFrame, base_path: Path) -> None:
        # Python ints → int64 en pandas; el parquet original usa INT32 (Spark IntegerType).
        # Construimos las columnas con tipos explícitos para que sea compatible.
        columns: dict[str, pa.Array] = {}
        for col in df.columns:
            if col == "categories":
                # ArrayType(IntegerType) en el parquet original → list<int32>
                columns[col] = pa.array(df[col].tolist(), type=pa.list_(pa.int32()))
            elif col in {"store_id", "customer_id", "category_id", "basket_size"}:
                columns[col] = pa.array(df[col].tolist(), type=pa.int32())
            else:
                columns[col] = pa.array(df[col].tolist(), type=pa.string())
        table = pa.table(columns)
        pq.write_to_dataset(
            table,
            root_path=str(base_path),
            partition_cols=["store_id", "year_month"],
            existing_data_behavior="overwrite_or_ignore",
        )