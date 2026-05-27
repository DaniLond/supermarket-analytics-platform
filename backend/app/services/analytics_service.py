"""Servicio de visualizaciones analíticas. Implementado en Sección 5."""

from datetime import date

import pandas as pd

from app.repositories.transaction_repo import TransactionRepository


class AnalyticsService:
    def __init__(self, repo: TransactionRepository) -> None:
        self._repo = repo

    def get_time_series(
        self,
        granularity: str = "day",
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> pd.DataFrame:
        return self._repo.time_series(granularity, start_date, end_date, store_id)
