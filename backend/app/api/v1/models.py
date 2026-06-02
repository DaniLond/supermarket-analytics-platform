"""Schemas Pydantic para entrada/salida de la API v1."""

from datetime import date as _Date

from pydantic import BaseModel, Field


class NewTransaction(BaseModel):
    date: _Date = Field(..., examples=["2013-07-01"])
    store_id: int = Field(..., examples=[102])
    customer_id: int = Field(..., examples=[999])
    categories: list[int] = Field(..., examples=[[1, 5, 10]])


class TransactionBatch(BaseModel):
    transactions: list[NewTransaction] = Field(..., min_length=1)


class RetrainResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    message: str = Field(..., examples=["Reentrenamiento completado"])


class ModelStatusResponse(BaseModel):
    segmentation_trained_at: str | None = Field(None, examples=["2013-06-30"])
    recommender_trained_at: str | None = Field(None, examples=["2013-06-30"])
    models_loaded: bool = Field(..., examples=[True])
