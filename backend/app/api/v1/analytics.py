"""Endpoints de Visualizaciones Analíticas"""

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_tx_repo
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.analytics import (
    BoxplotResponse,
    CorrelationHeatmapResponse,
    TimeSeriesResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter()


def _svc(repo: TransactionRepository = Depends(get_tx_repo)) -> AnalyticsService:
    return AnalyticsService(repo)


@router.get(
    "/time-series",
    response_model=TimeSeriesResponse,
    summary="Serie de tiempo de transacciones y líneas de categoría",
)
def time_series(
    granularity: str = Query("day", pattern="^(day|week|month)$"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    store_id: int | None = Query(None),
    svc: AnalyticsService = Depends(_svc),
) -> TimeSeriesResponse:
    return svc.get_time_series(granularity, start_date, end_date, store_id)


@router.get(
    "/boxplot",
    response_model=BoxplotResponse,
    summary="Distribución del tamaño de canasta por categoría o cliente",
)
def boxplot(
    dimension: str = Query("category", pattern="^(category|customer)$"),
    limit: int = Query(15, ge=1, le=50),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    store_id: int | None = Query(None),
    svc: AnalyticsService = Depends(_svc),
) -> BoxplotResponse:
    return svc.get_boxplot(dimension, limit, start_date, end_date, store_id)


@router.get(
    "/correlation-heatmap",
    response_model=CorrelationHeatmapResponse,
    summary="Correlación entre métricas de comportamiento del cliente",
)
def correlation_heatmap(
    svc: AnalyticsService = Depends(_svc),
) -> CorrelationHeatmapResponse:
    return svc.get_correlation_heatmap()