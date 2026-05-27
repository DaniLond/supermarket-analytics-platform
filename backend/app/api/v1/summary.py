"""Endpoints de Resumen Ejecutivo — implementados en Sección 4."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

router = APIRouter()

# TODO Sección 4: implementar endpoints con DuckDB + SummaryService
# GET /total-units
# GET /transaction-count
# GET /unique-customers
# GET /top-categories
# GET /top-customers
# GET /peak-days
# GET /category-share
