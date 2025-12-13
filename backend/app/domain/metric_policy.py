from dataclasses import dataclass
from typing import Dict, Literal, Optional

InsightType = Literal["change", "trend", "instability"]


@dataclass(frozen=True)
class ChangePolicy:
    z_threshold: float


@dataclass(frozen=True)
class TrendPolicy:
    slope_threshold: float


@dataclass(frozen=True)
class InstabilityPolicy:
    ratio_threshold: float


@dataclass(frozen=True)
class MetricPolicy:
    metric_key: str
    allowed_insights: set[InsightType]
    change: Optional[ChangePolicy] = None
    trend: Optional[TrendPolicy] = None
    instability: Optional[InstabilityPolicy] = None

