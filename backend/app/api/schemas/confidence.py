from __future__ import annotations

from pydantic import BaseModel
from typing import Literal, Optional, List


ConfidenceLevel = Literal["low", "medium", "high"]

UncertaintyReason = Literal[
    "insufficient_data",
    "high_variability",
    "short_duration",
    "confounding_signals",
    "inconsistent_effect"
]


class ConfidenceBreakdown(BaseModel):
    level: ConfidenceLevel
    score: float  # 0.0–1.0
    data_coverage_days: int
    consistency_ratio: float  # 0–1
    effect_size: Optional[float] = None
    uncertainty_reasons: List[UncertaintyReason] = []


class InsightUncertaintyUX(BaseModel):
    confidence: ConfidenceBreakdown
    interpretation_guidance: str
    safe_next_step: str

