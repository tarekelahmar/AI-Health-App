from typing import List
from pydantic import BaseModel


class MetricPoint(BaseModel):
    timestamp: str  # ISO datetime string
    value: float


class MetricBaseline(BaseModel):
    mean: float
    std: float


class MetricSeriesResponse(BaseModel):
    metric_key: str
    points: List[MetricPoint]
    baseline: MetricBaseline

