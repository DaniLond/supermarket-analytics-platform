from pydantic import BaseModel, Field


class ClusterProfile(BaseModel):
    cluster_id: int = Field(..., examples=[0])
    customer_count: int = Field(..., examples=[145])
    avg_frequency: float = Field(..., examples=[12.3])
    avg_unique_categories: float = Field(..., examples=[8.7])
    avg_basket_size: float = Field(..., examples=[5.2])
    avg_recency_days: float = Field(..., examples=[30.5])
    label: str = Field(..., examples=["Frecuente y activo"])


class ClusterProfilesResponse(BaseModel):
    clusters: list[ClusterProfile]


class ScatterPoint(BaseModel):
    customer_id: int = Field(..., examples=[530])
    pca_x: float = Field(..., examples=[1.23])
    pca_y: float = Field(..., examples=[-0.45])
    cluster: int = Field(..., examples=[0])


class ScatterResponse(BaseModel):
    points: list[ScatterPoint]


class CustomerClusterResponse(BaseModel):
    customer_id: int
    cluster: int
    frequency: float
    unique_categories: float
    avg_basket_size: float
    recency_days: float
    label: str