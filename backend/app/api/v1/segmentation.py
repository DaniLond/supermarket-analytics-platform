"""Endpoints de Segmentación K-Means"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_segmentation_repo
from app.repositories.segmentation_repo import SegmentationRepository
from app.schemas.segmentation import (
    ClusterProfilesResponse,
    CustomerClusterResponse,
    ScatterResponse,
)
from app.services.segmentation_service import SegmentationService

router = APIRouter()


def _svc(repo: SegmentationRepository = Depends(get_segmentation_repo)) -> SegmentationService:
    return SegmentationService(repo)


@router.get(
    "/clusters",
    response_model=ClusterProfilesResponse,
    summary="Perfiles promedio de cada clúster K-Means",
)
def get_clusters(svc: SegmentationService = Depends(_svc)) -> ClusterProfilesResponse:
    return svc.get_cluster_profiles()


@router.get(
    "/scatter",
    response_model=ScatterResponse,
    summary="Proyección PCA 2D de clientes coloreada por clúster",
)
def get_scatter(svc: SegmentationService = Depends(_svc)) -> ScatterResponse:
    return svc.get_scatter()


@router.get(
    "/customers/{customer_id}/cluster",
    response_model=CustomerClusterResponse,
    summary="Clúster al que pertenece un cliente específico",
)
def get_customer_cluster(
    customer_id: int,
    svc: SegmentationService = Depends(_svc),
) -> CustomerClusterResponse:
    result = svc.get_customer_cluster(customer_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Cliente {customer_id} no encontrado.")
    return result


@router.get(
    "/status",
    summary="Estado del modelo de segmentación (ready / training / error)",
)
def get_status() -> dict:
    from app.core.config import settings as _settings
    from app.db import state as _state
    return {
        "ready": _settings.customer_clusters_path.exists(),
        "training": _state.segmentation_training,
        "error": _state.segmentation_error,
    }


@router.post(
    "/retrain",
    summary="Reentrena el modelo K-Means con los datos actuales (tarda varios minutos)",
)
def retrain() -> dict:
    svc = SegmentationService()
    try:
        return svc.retrain()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))