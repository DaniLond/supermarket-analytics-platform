"""
Estado global de la aplicación
"""

from __future__ import annotations

import duckdb


class AppState:
    db: duckdb.DuckDBPyConnection | None = None
    transactions_loaded: bool = False
    models_loaded: bool = False
    segmentation_training: bool = False
    segmentation_error: str | None = None


state = AppState()