"""Endpoints de Recomendaciones FP-Growth"""

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_db, get_recommendations_repo
from app.repositories.recommendations_repo import RecommendationsRepository
from app.schemas.recommendations import (
    CategoryRecommendationsResponse,
    CustomerRecommendationsResponse,
    ProductsByCategoryResponse,
)
from app.services.recommender_service import RecommenderService

router = APIRouter()


def _svc(
    repo: RecommendationsRepository = Depends(get_recommendations_repo),
) -> RecommenderService:
    return RecommenderService(repo)


@router.get(
    "/categories",
    summary="Mapa category_id → nombre de todas las categorías",
)
def get_categories(
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> dict[int, str]:
    df = db.execute(
        "SELECT DISTINCT category_id, category_name FROM transactions_long ORDER BY category_id"
    ).df()
    return {int(row.category_id): row.category_name for _, row in df.iterrows()}


@router.get(
    "/status",
    summary="Estado del modelo FP-Growth (ready / training / error)",
)
def get_status() -> dict:
    from app.core.config import settings as _s
    from app.db import state as _state

    return {
        "ready": _s.association_rules_path.exists(),
        "training": _state.recommendations_training,
        "error": _state.recommendations_error,
    }


@router.get(
    "/category/{category_id}",
    response_model=CategoryRecommendationsResponse,
    summary="Reglas de asociación donde la categoría aparece como antecedente",
)
def rules_by_category(
    category_id: int,
    svc: RecommenderService = Depends(_svc),
) -> CategoryRecommendationsResponse:
    return svc.get_rules_for_category(category_id)


@router.get(
    "/customer/{customer_id}",
    response_model=CustomerRecommendationsResponse,
    summary="Categorías recomendadas para un cliente según su historial",
)
def rules_by_customer(
    customer_id: int,
    svc: RecommenderService = Depends(_svc),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> CustomerRecommendationsResponse:
    result = svc.get_rules_for_customer(customer_id, db)
    if not result.rules_used and not result.recommended_categories:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron recomendaciones para el cliente {customer_id}.",
        )
    return result


@router.get(
    "/products-by-category/{category_id}",
    response_model=ProductsByCategoryResponse,
    summary="Productos del catálogo pertenecientes a una categoría",
)
def products_by_category(
    category_id: int,
    svc: RecommenderService = Depends(_svc),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> ProductsByCategoryResponse:
    return svc.get_products_by_category(category_id, db)