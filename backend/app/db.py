"""
Estado global de la aplicación
"""

from __future__ import annotations

import duckdb


class AppState:
    db: duckdb.DuckDBPyConnection | None = None
    transactions_loaded: bool = False
    models_loaded: bool = False


state = AppState()