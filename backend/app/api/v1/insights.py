"""Insights endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List

from app.domain.models.insight import Insight
from app.domain.schemas.insight import InsightResponse
from app.core.database import get_db
from app.config.security import get_current_user
from app.config.rate_limiting import rate_limit_user, INSIGHT_RATE_LIMIT
from app.config.settings import get_settings
from app.domain.models.user import User
from app.engine.reasoning.insight_generator import (
    InsightEngine,
    generated_insight_to_dict,
)
from app.dependencies import get_insight_engine

router = APIRouter(tags=["insights"])
settings = get_settings()


@router.post("/sleep", summary="Generate sleep-related insights")
@rate_limit_user(settings.RATE_LIMIT_INSIGHTS if settings.ENABLE_RATE_LIMITING else "1000/minute")
def generate_sleep_insights(
    window_days: int = 30,
    current_user: User = Depends(get_current_user),
    engine: InsightEngine = Depends(get_insight_engine),
):
    """Generate sleep insights based on wearable data, HRV, and activity"""
    insight = engine.generate_sleep_insights(
        user_id=current_user.id,
        window_days=window_days,
    )
    if not insight:
        return {"detail": "Not enough data to generate sleep insights."}

    # Persist + return
    engine.persist_insight(insight)
    return generated_insight_to_dict(insight)


@router.get("/", response_model=List[InsightResponse])
def list_insights(
    insight_type: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all insights for current user, optionally filtered by type"""
    query = db.query(Insight).filter(Insight.user_id == current_user.id)
    if insight_type:
        query = query.filter(Insight.insight_type == insight_type)
    return query.order_by(Insight.generated_at.desc()).all()


@router.get("/{insight_id}", response_model=InsightResponse)
def get_insight(
    insight_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific insight"""
    insight = db.query(Insight).filter(
        Insight.id == insight_id,
        Insight.user_id == current_user.id
    ).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    return insight

