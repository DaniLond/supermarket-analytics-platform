from pydantic import BaseModel, Field


class TimeSeriesPoint(BaseModel):
    period: str = Field(..., examples=["2013-01-01"])
    transactions: int = Field(..., examples=[1200])
    category_lines: int = Field(..., examples=[4800])


class TimeSeriesResponse(BaseModel):
    granularity: str = Field(..., examples=["day"])
    points: list[TimeSeriesPoint]


class BoxplotStats(BaseModel):
    label: str = Field(..., examples=["PANES-TOSTADAS"])
    min: float
    q1: float
    median: float
    q3: float
    max: float
    outliers: list[float] = Field(default_factory=list)


class BoxplotResponse(BaseModel):
    dimension: str = Field(..., examples=["category"])
    stats: list[BoxplotStats]


class CorrelationCell(BaseModel):
    feature_x: str = Field(..., examples=["frequency"])
    feature_y: str = Field(..., examples=["avg_basket_size"])
    correlation: float = Field(..., examples=[0.72])


class CorrelationHeatmapResponse(BaseModel):
    features: list[str]
    cells: list[CorrelationCell]
