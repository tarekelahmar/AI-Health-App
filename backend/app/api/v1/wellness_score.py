"""
Wellness Score API endpoints.

- POST /compute — compute (or recompute) score for a date
- GET /{date} — get score for a specific date
- GET /history — score timeline for last N days
"""

from datetime import date
from typing import List, Optional

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.core.database import get_db
from app.engine import wellness_score_service

router = make_v1_router(prefix="/api/v1/wellness-score", tags=["wellness-score"])


# ── Schemas ──────────────────────────────────────────────────────


class ContributingFactorResponse(BaseModel):
    metric_key: str
    label: str
    z_score: float
    weight: float
    direction: str
    category: Optional[str] = None


class WellnessScoreResponse(BaseModel):
    id: int
    user_id: int
    score_date: date
    score: float
    objective_score: Optional[float] = None
    subjective_score: Optional[float] = None
    contributing_factors: List[ContributingFactorResponse] = []

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, ws) -> "WellnessScoreResponse":
        factors = ws.contributing_factors_json or []
        return cls(
            id=ws.id,
            user_id=ws.user_id,
            score_date=ws.score_date,
            score=ws.score,
            objective_score=ws.objective_score,
            subjective_score=ws.subjective_score,
            contributing_factors=[ContributingFactorResponse(**f) for f in factors],
        )


class ComputeRequest(BaseModel):
    score_date: Optional[str] = None  # ISO date string, defaults to today


# ── Endpoints ────────────────────────────────────────────────────


@router.post("/compute", response_model=WellnessScoreResponse)
def compute_score(
    payload: ComputeRequest,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Compute (or recompute) wellness score for a date."""
    from datetime import date as date_type
    target = date_type.fromisoformat(payload.score_date) if payload.score_date else None
    ws = wellness_score_service.compute_and_store(
        db=db,
        user_id=user_id,
        target_date=target,
    )
    return WellnessScoreResponse.from_model(ws)


@router.get("/history", response_model=List[WellnessScoreResponse])
def get_history(
    days: int = Query(30, ge=1, le=365),
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Get wellness score history for last N days."""
    scores = wellness_score_service.get_score_history(db=db, user_id=user_id, days=days)
    return [WellnessScoreResponse.from_model(ws) for ws in scores]


@router.get("/{score_date}", response_model=Optional[WellnessScoreResponse])
def get_score(
    score_date: date,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Get wellness score for a specific date."""
    ws = wellness_score_service.get_score(db=db, user_id=user_id, target_date=score_date)
    if ws is None:
        return None
    return WellnessScoreResponse.from_model(ws)
