"""Endpoints de Resumen Ejecutivo"""

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_tx_repo
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.summary import (
    CategoryShareResponse,
    KpiResponse,
    PeakDaysResponse,
    TopCategoriesResponse,
    TopCustomersResponse,
)
from app.services.summary_service import SummaryService

router = APIRouter()

_STORES = [102, 103, 107, 110]


def _svc(repo: TransactionRepository = Depends(get_tx_repo)) -> SummaryService:
    return SummaryService(repo)


# ---------------------------------------------------------------------------
# KPI simples
# ---------------------------------------------------------------------------

@router.get(
    "/total-units",
    response_model=KpiResponse,
    summary="Total de ventas (unidades de categoría vendidas)",
)
def total_units(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    store_id: int | None = Query(None),
    svc: SummaryService = Depends(_svc),
) -> KpiResponse:
    value = svc.get_total_lines(start_date, end_date, store_id)
    return KpiResponse(value=value, label="Total de ventas")


@router.get(
    "/transaction-count",
    response_model=KpiResponse,
    summary="Número de transacciones únicas",
)
def transaction_count(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    store_id: int | None = Query(None),
    svc: SummaryService = Depends(_svc),
) -> KpiResponse:
    value = svc.get_transaction_count(start_date, end_date, store_id)
    return KpiResponse(value=value, label="Transacciones únicas")


@router.get(
    "/unique-customers",
    response_model=KpiResponse,
    summary="Clientes únicos en el período",
)
def unique_customers(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    store_id: int | None = Query(None),
    svc: SummaryService = Depends(_svc),
) -> KpiResponse:
    value = svc.get_unique_customers(start_date, end_date, store_id)
    return KpiResponse(value=value, label="Clientes únicos")


# ---------------------------------------------------------------------------
# Rankings
# ---------------------------------------------------------------------------

@router.get(
    "/top-categories",
    response_model=TopCategoriesResponse,
    summary="Top N categorías por volumen y frecuencia",
)
def top_categories(
    limit: int = Query(10, ge=1, le=50),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    store_id: int | None = Query(None),
    svc: SummaryService = Depends(_svc),
) -> TopCategoriesResponse:
    return svc.get_top_categories(limit, start_date, end_date, store_id)


@router.get(
    "/top-customers",
    response_model=TopCustomersResponse,
    summary="Top N clientes por transacciones y diversidad",
)
def top_customers(
    limit: int = Query(10, ge=1, le=50),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    store_id: int | None = Query(None),
    svc: SummaryService = Depends(_svc),
) -> TopCustomersResponse:
    return svc.get_top_customers(limit, start_date, end_date, store_id)


# ---------------------------------------------------------------------------
# Heatmap y share
# ---------------------------------------------------------------------------

@router.get(
    "/peak-days",
    response_model=PeakDaysResponse,
    summary="Distribución de transacciones por día de semana × día de mes",
)
def peak_days(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    store_id: int | None = Query(None),
    svc: SummaryService = Depends(_svc),
) -> PeakDaysResponse:
    return svc.get_peak_days(start_date, end_date, store_id)


@router.get(
    "/category-share",
    response_model=CategoryShareResponse,
    summary="Participación porcentual de cada categoría en el volumen total",
)
def category_share(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    store_id: int | None = Query(None),
    svc: SummaryService = Depends(_svc),
) -> CategoryShareResponse:
    return svc.get_category_share(start_date, end_date, store_id)