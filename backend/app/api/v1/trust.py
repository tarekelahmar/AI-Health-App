from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.domain.models.trust_score import TrustScore
from app.engine.trust.trust_engine import TrustEngine

router = make_v1_router(prefix="/api/v1/trust", tags=["trust"])


@router.get("")
def get_trust_score(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Get trust score breakdown for a user"""
    trust_engine = TrustEngine(db)
    
    # Compute/update trust score
    trust_score = trust_engine.compute_trust_score(user_id)
    trust_level = trust_engine.get_trust_level(user_id)
    
    return {
        "user_id": user_id,
        "overall_score": trust_score.score,
        "trust_level": trust_level,
        "components": {
            "data_coverage": trust_score.data_coverage_score,
            "adherence": trust_score.adherence_score,
            "evaluation_success_rate": trust_score.evaluation_success_rate,
            "stability": trust_score.stability_score,
        },
        "last_updated": trust_score.last_updated_at.isoformat(),
        "interpretation": _interpret_trust_score(trust_score.score, trust_level),
    }


def _interpret_trust_score(score: float, level: str) -> str:
    """Generate human-readable interpretation of trust score"""
    if level == "high":
        return (
            f"High trust ({score:.1f}/100). The system has strong confidence in its recommendations "
            "based on your data history, adherence patterns, and successful evaluations."
        )
    elif level == "medium":
        return (
            f"Medium trust ({score:.1f}/100). The system is building confidence. "
            "More consistent data and adherence will improve recommendation quality."
        )
    else:
        return (
            f"Low trust ({score:.1f}/100). The system is still learning about your patterns. "
            "Continue logging data and following protocols to build trust over time."
        )

