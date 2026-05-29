"""Servicio de visualizaciones analíticas."""

from datetime import date

from app.repositories.transaction_repo import TransactionRepository
from app.schemas.analytics import (
    BoxplotResponse,
    BoxplotStats,
    CorrelationCell,
    CorrelationHeatmapResponse,
    TimeSeriesPoint,
    TimeSeriesResponse,
)


class AnalyticsService:
    def __init__(self, repo: TransactionRepository) -> None:
        self._repo = repo

    def get_time_series(
        self,
        granularity: str = "day",
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> TimeSeriesResponse:
        df = self._repo.time_series(granularity, start_date, end_date, store_id)
        points = [
            TimeSeriesPoint(
                period=str(row.period)[:10],
                transactions=int(row.transactions),
                category_lines=int(row.category_lines),
            )
            for row in df.itertuples()
        ]
        return TimeSeriesResponse(granularity=granularity, points=points)

    def get_boxplot(
        self,
        dimension: str = "category",
        limit: int = 15,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: int | None = None,
    ) -> BoxplotResponse:
        df = self._repo.boxplot(dimension, limit, start_date, end_date, store_id)
        stats = [
            BoxplotStats(
                label=str(row.label),
                min=float(row.min_val),
                q1=float(row.q1),
                median=float(row.median),
                q3=float(row.q3),
                max=float(row.max_val),
                outliers=[],
            )
            for row in df.itertuples()
        ]
        return BoxplotResponse(dimension=dimension, stats=stats)

    def get_correlation_heatmap(self) -> CorrelationHeatmapResponse:
        df = self._repo.correlation_heatmap()
        corr = df[["frequency", "unique_categories", "avg_basket_size"]].corr()
        features = list(corr.columns)
        cells = [
            CorrelationCell(
                feature_x=fx,
                feature_y=fy,
                correlation=round(float(corr.loc[fx, fy]), 3),
            )
            for fx in features
            for fy in features
        ]
        return CorrelationHeatmapResponse(features=features, cells=cells)