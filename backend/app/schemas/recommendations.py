from pydantic import BaseModel, Field


class AssociationRuleOut(BaseModel):
    antecedent: list[int] = Field(..., examples=[[5, 10]])
    consequent: list[int] = Field(..., examples=[[3]])
    support: float = Field(..., examples=[0.05])
    confidence: float = Field(..., examples=[0.72])
    lift: float = Field(..., examples=[2.1])


class CategoryRecommendationsResponse(BaseModel):
    category_id: int = Field(..., examples=[5])
    rules: list[AssociationRuleOut]


class CustomerRecommendationsResponse(BaseModel):
    customer_id: int = Field(..., examples=[530])
    cluster: int | None = Field(None, examples=[2])
    recommended_categories: list[int] = Field(..., examples=[[3, 7, 12]])
    rules_used: list[AssociationRuleOut]


class ProductInfo(BaseModel):
    product_code: int = Field(..., examples=[1007])
    category_id: int = Field(..., examples=[1])


class ProductsByCategoryResponse(BaseModel):
    category_id: int = Field(..., examples=[1])
    products: list[ProductInfo]


class ClusterProfile(BaseModel):
    cluster_id: int = Field(..., examples=[0])
    customer_count: int = Field(..., examples=[450])
    avg_frequency: float = Field(..., examples=[12.3])
    avg_unique_categories: float = Field(..., examples=[8.5])
    avg_basket_size: float = Field(..., examples=[4.2])
    avg_recency_days: float = Field(..., examples=[15.0])
    label: str = Field(..., examples=["Compradores frecuentes"])


class ScatterPoint(BaseModel):
    customer_id: int
    pca_x: float
    pca_y: float
    cluster: int
