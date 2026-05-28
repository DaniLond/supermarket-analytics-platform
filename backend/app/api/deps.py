"""
Dependencias de inyección — proveedores de conexión DuckDB y repositorios.
"""

import duckdb
from fastapi import Depends, HTTPException

from app.core.config import settings
from app.db import state
from app.repositories.catalog_repo import CatalogRepository
from app.repositories.transaction_repo import TransactionRepository


def get_db():
    """Abre una conexión DuckDB en memoria por request con vistas sobre los Parquet."""
    if not state.transactions_loaded:
        raise HTTPException(
            status_code=503,
            detail="Datos no cargados. Ejecuta POST /api/v1/ingest primero.",
        )
    conn = duckdb.connect(":memory:")
    long_path = settings.transactions_long_path
    basket_path = settings.transactions_basket_path
    catalog_path = settings.catalog_path
    conn.execute(
        f"CREATE VIEW transactions_long AS "
        f"SELECT * FROM read_parquet('{long_path.as_posix()}/**/*.parquet', hive_partitioning=true)"
    )
    conn.execute(
        f"CREATE VIEW transactions_basket AS "
        f"SELECT * FROM read_parquet('{basket_path.as_posix()}/**/*.parquet', hive_partitioning=true)"
    )
    if catalog_path.exists():
        conn.execute(
            f"CREATE VIEW catalog AS "
            f"SELECT * FROM read_parquet('{catalog_path.as_posix()}/*.parquet')"
        )
    try:
        yield conn
    finally:
        conn.close()


def get_tx_repo(
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> TransactionRepository:
    return TransactionRepository(db)


def get_catalog_repo(
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> CatalogRepository:
    return CatalogRepository(db)