"""Insights endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.domain.models.insight import Insight
from app.domain.schemas.insight import InsightResponse
from app.core.database import get_db
from app.config.security import get_current_user
from app.domain.models.user import User

router = APIRouter()

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

