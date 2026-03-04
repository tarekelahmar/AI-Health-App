"""
Life Domain API endpoints.

GET /current   → current scores (10 floats)
GET /history   → score history for comparison overlays
"""

from typing import List

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.api.schemas.life_domains import LifeDomainScoreResponse
from app.core.database import get_db
from app.domain.models.life_domain_score import LIFE_DOMAINS, DEFAULT_SCORE, LifeDomainScore

router = make_v1_router(prefix="/api/v1/life-domains", tags=["life-domains"])


@router.get("/current", response_model=LifeDomainScoreResponse)
def get_current_scores(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Get the most recent life domain scores for the user."""
    row = (
        db.query(LifeDomainScore)
        .filter(LifeDomainScore.user_id == user_id)
        .order_by(LifeDomainScore.score_date.desc())
        .first()
    )

    if not row:
        # Cold start: return defaults
        return LifeDomainScoreResponse(
            score_date="",
            scores={d: DEFAULT_SCORE for d in LIFE_DOMAINS},
            total_score=DEFAULT_SCORE * len(LIFE_DOMAINS),
        )

    return LifeDomainScoreResponse(
        score_date=row.score_date,
        scores=row.get_scores(),
        total_score=row.total_score,
    )


@router.get("/history", response_model=List[LifeDomainScoreResponse])
def get_score_history(
    days: int = Query(30, ge=1, le=365),
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Get life domain score history for comparison overlays."""
    from datetime import date, timedelta

    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = (
        db.query(LifeDomainScore)
        .filter(
            LifeDomainScore.user_id == user_id,
            LifeDomainScore.score_date >= cutoff,
        )
        .order_by(LifeDomainScore.score_date.asc())
        .all()
    )

    return [
        LifeDomainScoreResponse(
            score_date=r.score_date,
            scores=r.get_scores(),
            total_score=r.total_score,
        )
        for r in rows
    ]
