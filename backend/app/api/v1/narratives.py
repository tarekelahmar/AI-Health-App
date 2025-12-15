from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.schemas.narratives import (
    NarrativeResponse,
    NarrativeListResponse,
    GenerateNarrativeRequest,
)
from app.domain.repositories.narrative_repository import NarrativeRepository
from app.engine.synthesis.narrative_synthesizer import generate_and_persist_narrative
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/api/v1/narratives", tags=["narratives"])


@router.get("/daily", response_model=NarrativeResponse)
def get_daily_narrative(
    user_id: int = Depends(get_request_user_id),
    day: date = Query(...),
    db: Session = Depends(get_db),
):
    repo = NarrativeRepository(db)
    obj = repo.get_for_period(user_id=user_id, period_type="daily", period_start=day, period_end=day)
    if obj:
        return _to_schema(obj)
    obj = generate_and_persist_narrative(db, user_id=user_id, period_type="daily", start=day, end=day)
    return _to_schema(obj)


@router.get("/weekly", response_model=NarrativeResponse)
def get_weekly_narrative(
    user_id: int = Depends(get_request_user_id),
    week_start: date = Query(..., description="Monday (recommended)"),
    db: Session = Depends(get_db),
):
    week_end = week_start + timedelta(days=6)
    repo = NarrativeRepository(db)
    obj = repo.get_for_period(user_id=user_id, period_type="weekly", period_start=week_start, period_end=week_end)
    if obj:
        return _to_schema(obj)
    obj = generate_and_persist_narrative(db, user_id=user_id, period_type="weekly", start=week_start, end=week_end)
    return _to_schema(obj)


@router.post("/generate", response_model=NarrativeResponse)
def generate_narrative(
    req: GenerateNarrativeRequest,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db)
):
    # Override req.user_id with authenticated user_id (prevent spoofing)
    req.user_id = user_id
    if req.period_type == "daily":
        if req.date is None:
            raise HTTPException(status_code=400, detail="date is required for daily narratives")
        obj = generate_and_persist_narrative(
            db,
            user_id=req.user_id,
            period_type="daily",
            start=req.date,
            end=req.date,
            include_llm_translation=req.include_llm_translation,
        )
        return _to_schema(obj)

    if req.week_start_date is None:
        raise HTTPException(status_code=400, detail="week_start_date is required for weekly narratives")
    week_end = req.week_start_date + timedelta(days=6)
    obj = generate_and_persist_narrative(
        db,
        user_id=req.user_id,
        period_type="weekly",
        start=req.week_start_date,
        end=week_end,
        include_llm_translation=req.include_llm_translation,
    )
    return _to_schema(obj)


@router.get("", response_model=NarrativeListResponse)
def list_recent_narratives(
    user_id: int = Depends(get_request_user_id),
    period_type: str = Query("daily"),
    limit: int = Query(14, ge=1, le=100),
    db: Session = Depends(get_db),
):
    repo = NarrativeRepository(db)
    items = repo.list_recent(user_id=user_id, period_type=period_type, limit=limit)
    return {"count": len(items), "items": [_to_schema(x) for x in items]}


def _to_schema(obj) -> NarrativeResponse:
    # Normalize JSON fields to expected names
    return NarrativeResponse(
        id=obj.id,
        user_id=obj.user_id,
        period_type=obj.period_type,
        period_start=obj.period_start,
        period_end=obj.period_end,
        title=obj.title,
        summary=obj.summary,
        key_points=obj.key_points_json or [],
        drivers=obj.drivers_json or [],
        actions=obj.actions_json or [],
        risks=obj.risks_json or [],
        metadata=obj.metadata_json or {},
        created_at=obj.created_at,
    )

