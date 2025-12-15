from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.engine.synthesis.synthesis_service import SynthesisService
from app.domain.repositories.insight_summary_repository import InsightSummaryRepository
from app.api.schemas.summaries import InsightSummaryResponse
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/api/v1/summaries", tags=["summaries"])


@router.post("/daily", response_model=InsightSummaryResponse)
def run_daily_summary(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    service = SynthesisService(db)
    summary = service.run_daily(user_id)
    return InsightSummaryResponse(
        id=summary.id,
        user_id=summary.user_id,
        period=summary.period,
        summary_date=summary.summary_date.isoformat(),
        headline=summary.headline,
        narrative=summary.narrative,
        key_metrics=summary.key_metrics,
        drivers=summary.drivers,
        interventions=summary.interventions,
        outcomes=summary.outcomes,
        confidence=summary.confidence,
    )


@router.get("/latest", response_model=Optional[InsightSummaryResponse])
def get_latest(
    user_id: int = Depends(get_request_user_id),
    period: str = Query("daily"),
    db: Session = Depends(get_db),
):
    repo = InsightSummaryRepository(db)
    summary = repo.get_latest(user_id, period)
    if not summary:
        return None
    return InsightSummaryResponse(
        id=summary.id,
        user_id=summary.user_id,
        period=summary.period,
        summary_date=summary.summary_date.isoformat(),
        headline=summary.headline,
        narrative=summary.narrative,
        key_metrics=summary.key_metrics,
        drivers=summary.drivers,
        interventions=summary.interventions,
        outcomes=summary.outcomes,
        confidence=summary.confidence,
    )

