from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class AttributionResult:
    """Result of lagged effect attribution analysis"""
    user_id: int
    metric_key: str
    intervention_id: int
    lag_days: int
    effect_size: float
    direction: str  # "improved" | "worsened" | "no_change"
    confidence: float  # 0..1
    coverage: float  # 0..1
    interaction: Optional[str] = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

