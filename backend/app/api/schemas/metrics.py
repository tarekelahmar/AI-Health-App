from typing import List, Optional
from pydantic import BaseModel


class MetricPoint(BaseModel):
    timestamp: str  # ISO datetime string
    value: float


class MetricBaseline(BaseModel):
    """
    AUDIT FIX: Baseline can be null/unknown instead of misleading 0/0.
    """
    mean: Optional[float] = None
    std: Optional[float] = None
    available: bool = True  # False if baseline not computed yet
    reason: Optional[str] = None  # Why baseline is unavailable (e.g., "insufficient_data")


class MetricSeriesResponse(BaseModel):
    metric_key: str
    points: List[MetricPoint]
    baseline: MetricBaseline

