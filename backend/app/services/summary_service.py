"""Servicio de KPIs del Resumen Ejecutivo."""

from datetime import date

from app.repositories.transaction_repo import TransactionRepository
from app.schemas.summary import (
    CategoryShare,
    CategoryShareResponse,
    CategoryStat,
    CustomerStat,
    PeakDayCell,
    PeakDaysResponse,
    TopCategoriesResponse,
    TopCustomersResponse,
)


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

    def get_top_categories(
        self,
        limit: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> TopCategoriesResponse:
        df = self._repo.top_categories(limit, start_date, end_date, store_id)
        rows = df.to_dict("records")
        by_volume = [
            CategoryStat(
                category_id=int(r["category_id"]),
                category_name=str(r["category_name"]),
                volume=int(r["volume"]),
                frequency=int(r["frequency"]),
            )
            for r in rows
        ]
        by_frequency = [
            CategoryStat(
                category_id=int(r["category_id"]),
                category_name=str(r["category_name"]),
                volume=int(r["volume"]),
                frequency=int(r["frequency"]),
            )
            for r in sorted(rows, key=lambda x: x["frequency"], reverse=True)
        ]
        return TopCategoriesResponse(by_volume=by_volume, by_frequency=by_frequency)

    def get_top_customers(
        self,
        limit: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> TopCustomersResponse:
        df = self._repo.top_customers(limit, start_date, end_date, store_id)
        rows = df.to_dict("records")
        by_transactions = [
            CustomerStat(
                customer_id=int(r["customer_id"]),
                transaction_count=int(r["transaction_count"]),
                unique_categories=int(r["unique_categories"]),
            )
            for r in rows
        ]
        by_diversity = [
            CustomerStat(
                customer_id=int(r["customer_id"]),
                transaction_count=int(r["transaction_count"]),
                unique_categories=int(r["unique_categories"]),
            )
            for r in sorted(rows, key=lambda x: x["unique_categories"], reverse=True)
        ]
        return TopCustomersResponse(by_transactions=by_transactions, by_diversity=by_diversity)

    def get_peak_days(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> PeakDaysResponse:
        df = self._repo.peak_days(start_date, end_date, store_id)
        cells = [
            PeakDayCell(
                day_of_week=int(r["day_of_week"]),
                day_of_month=int(r["day_of_month"]),
                transaction_count=int(r["transaction_count"]),
            )
            for r in df.to_dict("records")
        ]
        return PeakDaysResponse(cells=cells)

    def get_category_share(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> CategoryShareResponse:
        df = self._repo.category_share(start_date, end_date, store_id)
        shares = [
            CategoryShare(
                category_id=int(r["category_id"]),
                category_name=str(r["category_name"]),
                volume=int(r["volume"]),
                share_pct=float(r["share_pct"]),
            )
            for r in df.to_dict("records")
        ]
        return CategoryShareResponse(shares=shares)