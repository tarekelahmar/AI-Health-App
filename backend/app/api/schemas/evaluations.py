from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Literal

from pydantic import BaseModel, Field

Verdict = Literal["helpful", "not_helpful", "unclear", "insufficient_data"]


class EvaluationResultResponse(BaseModel):
    id: int
    user_id: int
    experiment_id: int
    metric_key: str

    baseline_mean: float
    baseline_std: float
    intervention_mean: float
    intervention_std: float

    delta: float
    percent_change: float
    effect_size: float

    coverage: float = Field(ge=0.0, le=1.0)
    adherence_rate: float = Field(ge=0.0, le=1.0)
    
    # SECURITY FIX (Risk #7): Confidence and adherence evidence
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Confidence score (0-1) based on effect size, coverage, and adherence")
    has_adherence_evidence: bool = Field(default=False, description="Whether adherence events were logged for this evaluation")

    verdict: Verdict
    created_at: datetime

    details: Dict[str, Any]


class EvaluateExperimentRequest(BaseModel):
    baseline_days: int = Field(default=14, ge=7, le=60)
    intervention_days: int = Field(default=14, ge=7, le=60)
    min_coverage: float = Field(default=0.60, ge=0.10, le=1.0)
    min_points: int = Field(default=7, ge=3, le=60)


# Legacy schema for backward compatibility
class EvaluationOut(BaseModel):
    id: int
    user_id: int
    experiment_id: int
    verdict: Verdict
    summary: str
    pre_mean: Optional[float] = None
    post_mean: Optional[float] = None
    delta: Optional[float] = None
    effect_size: Optional[float] = None
    data_coverage: Optional[float] = None
    confidence: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

