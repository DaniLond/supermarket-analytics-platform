"""
Entidades de dominio — representaciones puras, sin dependencias de framework.
Usadas como tipos intermedios entre repositorios y servicios.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Transaction:
    transaction_id: str
    date: date
    store_id: int
    customer_id: int
    categories: list[int]
    basket_size: int


@dataclass
class TransactionLine:
    """Versión 'long' de una transacción: una fila por categoría."""
    transaction_id: str
    date: date
    store_id: int
    customer_id: int
    category_id: int
    category_name: str


@dataclass
class Category:
    category_id: int
    category_name: str


@dataclass
class Product:
    product_code: int
    category_id: int


@dataclass
class CustomerProfile:
    customer_id: int
    frequency: int
    total_categories_bought: int
    unique_categories: int
    avg_basket_size: float
    recency_days: int
    cluster: int | None = None


@dataclass
class AssociationRule:
    antecedent: list[int]
    consequent: list[int]
    support: float
    confidence: float
    lift: float
