"""Servicio de KPIs del Resumen Ejecutivo. Implementado en Sección 4."""

from datetime import date

from app.repositories.transaction_repo import TransactionRepository


class SummaryService:
    def __init__(self, repo: TransactionRepository) -> None:
        self._repo = repo

    def get_total_lines(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> int:
        return self._repo.total_lines(start_date, end_date, store_id)

    def get_transaction_count(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> int:
        return self._repo.transaction_count(start_date, end_date, store_id)

    def get_unique_customers(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> int:
        return self._repo.unique_customers(start_date, end_date, store_id)
