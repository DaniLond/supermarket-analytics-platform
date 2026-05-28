"""
Repositorio de transacciones
"""

import logging
from datetime import date

import duckdb
import pandas as pd

logger = logging.getLogger("supermercado.repos.transactions")


class TransactionRepository:
    def __init__(self, db: duckdb.DuckDBPyConnection) -> None:
        self._db = db

    def _date_filter(
        self,
        start_date: date | None,
        end_date: date | None,
        store_id: int | None,
    ) -> tuple[str, list]:
        clauses: list[str] = []
        params: list = []
        if start_date:
            clauses.append("date >= ?")
            params.append(str(start_date))
        if end_date:
            clauses.append("date <= ?")
            params.append(str(end_date))
        if store_id is not None:
            clauses.append("store_id = ?")
            params.append(store_id)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return where, params

    def total_lines(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> int:
        where, params = self._date_filter(start_date, end_date, store_id)
        row = self._db.execute(
            f"SELECT COUNT(*) FROM transactions_long {where}", params
        ).fetchone()
        return row[0] if row else 0

    def transaction_count(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> int:
        where, params = self._date_filter(start_date, end_date, store_id)
        row = self._db.execute(
            f"SELECT COUNT(DISTINCT transaction_id) FROM transactions_long {where}", params
        ).fetchone()
        return row[0] if row else 0

    def unique_customers(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> int:
        where, params = self._date_filter(start_date, end_date, store_id)
        row = self._db.execute(
            f"SELECT COUNT(DISTINCT customer_id) FROM transactions_long {where}", params
        ).fetchone()
        return row[0] if row else 0

    def top_categories(
        self,
        limit: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> pd.DataFrame:
        where, params = self._date_filter(start_date, end_date, store_id)
        return self._db.execute(
            f"""
            SELECT category_id, category_name,
                   COUNT(*) AS volume,
                   COUNT(DISTINCT transaction_id) AS frequency
            FROM transactions_long {where}
            GROUP BY category_id, category_name
            ORDER BY volume DESC
            LIMIT {limit}
            """,
            params,
        ).df()

    def top_customers(
        self,
        limit: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> pd.DataFrame:
        where, params = self._date_filter(start_date, end_date, store_id)
        return self._db.execute(
            f"""
            SELECT customer_id,
                   COUNT(DISTINCT transaction_id) AS transaction_count,
                   COUNT(DISTINCT category_id)    AS unique_categories
            FROM transactions_long {where}
            GROUP BY customer_id
            ORDER BY transaction_count DESC
            LIMIT {limit}
            """,
            params,
        ).df()

    def peak_days(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> pd.DataFrame:
        where, params = self._date_filter(start_date, end_date, store_id)
        return self._db.execute(
            f"""
            SELECT DAYOFWEEK(date::DATE)  AS day_of_week,
                   DAY(date::DATE)        AS day_of_month,
                   COUNT(DISTINCT transaction_id) AS transaction_count
            FROM transactions_long {where}
            GROUP BY day_of_week, day_of_month
            ORDER BY day_of_week, day_of_month
            """,
            params,
        ).df()

    def category_share(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> pd.DataFrame:
        where, params = self._date_filter(start_date, end_date, store_id)
        return self._db.execute(
            f"""
            SELECT category_id, category_name,
                   COUNT(*) AS volume,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS share_pct
            FROM transactions_long {where}
            GROUP BY category_id, category_name
            ORDER BY volume DESC
            """,
            params,
        ).df()

    def time_series(
        self,
        granularity: str = "day",
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> pd.DataFrame:
        granularity_expr = {
            "day": "date",
            "week": "DATE_TRUNC('week', date)",
            "month": "DATE_TRUNC('month', date)",
        }.get(granularity, "date")
        where, params = self._date_filter(start_date, end_date, store_id)
        return self._db.execute(
            f"""
            SELECT {granularity_expr} AS period,
                   COUNT(DISTINCT transaction_id) AS transactions,
                   COUNT(*) AS category_lines
            FROM transactions_long {where}
            GROUP BY period
            ORDER BY period
            """,
            params,
        ).df()

    def insert_transactions(self, rows: list[dict]) -> int:
        import pandas as pd

        df = pd.DataFrame(rows)
        self._db.execute("INSERT INTO transactions_long SELECT * FROM df")
        return len(df)
