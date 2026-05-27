from pydantic import BaseModel, Field


class KpiResponse(BaseModel):
    value: int = Field(..., examples=[314000])
    label: str = Field(..., examples=["Total líneas de categoría"])


class CategoryStat(BaseModel):
    category_id: int = Field(..., examples=[5])
    category_name: str = Field(..., examples=["PANES-TOSTADAS"])
    volume: int = Field(..., examples=[12500])
    frequency: int = Field(..., examples=[8300])


class TopCategoriesResponse(BaseModel):
    by_volume: list[CategoryStat]
    by_frequency: list[CategoryStat]


class CustomerStat(BaseModel):
    customer_id: int = Field(..., examples=[530])
    transaction_count: int = Field(..., examples=[45])
    unique_categories: int = Field(..., examples=[20])


class TopCustomersResponse(BaseModel):
    by_transactions: list[CustomerStat]
    by_diversity: list[CustomerStat]


class PeakDayCell(BaseModel):
    day_of_week: int = Field(..., examples=[1], description="1=Lun, 7=Dom")
    day_of_month: int = Field(..., examples=[15])
    transaction_count: int = Field(..., examples=[320])


class PeakDaysResponse(BaseModel):
    cells: list[PeakDayCell]


class CategoryShare(BaseModel):
    category_id: int = Field(..., examples=[3])
    category_name: str = Field(..., examples=["VERDURAS DE FRUTOS"])
    volume: int = Field(..., examples=[9800])
    share_pct: float = Field(..., examples=[4.5])


class CategoryShareResponse(BaseModel):
    shares: list[CategoryShare]
