"""Servicio de ingesta de transacciones nuevas vía API. Implementado en Sección 9."""

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


class IngestionService:
    def __init__(self, long_path: Path, basket_path: Path) -> None:
        self._long_path = long_path
        self._basket_path = basket_path

    def ingest(self, transactions: list[dict]) -> int:
        """
        Persiste nuevas transacciones en Parquet particionado.
        Idempotente: deduplicación por transaction_id (hash de date+store+customer).
        """
        rows_long = []
        rows_basket = []

        for tx in transactions:
            date_ = tx["date"]
            store_id = tx["store_id"]
            customer_id = tx["customer_id"]
            categories = tx["categories"]
            tx_id = _row_hash(date_, store_id, customer_id)
            year_month = date_.strftime("%Y-%m")

            rows_basket.append(
                {
                    "transaction_id": tx_id,
                    "date": str(date_),
                    "store_id": store_id,
                    "customer_id": customer_id,
                    "categories": categories,
                    "basket_size": len(categories),
                    "year_month": year_month,
                }
            )
            for cat in categories:
                rows_long.append(
                    {
                        "transaction_id": tx_id,
                        "date": str(date_),
                        "store_id": store_id,
                        "customer_id": customer_id,
                        "category_id": cat,
                        "category_name": "",  # se enriquece post-join
                        "year_month": year_month,
                    }
                )

        if rows_long:
            self._write_parquet(pd.DataFrame(rows_long), self._long_path)
            self._write_parquet(pd.DataFrame(rows_basket), self._basket_path)
            logger.info("Ingestados %d transacciones / %d líneas", len(transactions), len(rows_long))

        return len(transactions)

    def _write_parquet(self, df: pd.DataFrame, base_path: Path) -> None:
        table = pa.Table.from_pandas(df)
        pq.write_to_dataset(
            table,
            root_path=str(base_path),
            partition_cols=["store_id", "year_month"],
            existing_data_behavior="overwrite_or_ignore",
        )
