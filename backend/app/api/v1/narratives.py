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
from app.api.consent_gate import require_user_and_consent
from app.api.router_factory import make_v1_router
from app.domain.health_domains import domain_for_signal

router = make_v1_router(prefix="/api/v1/narratives", tags=["narratives"])


@router.get("/daily", response_model=NarrativeResponse)
def get_daily_narrative(
    user_id: int = Depends(require_user_and_consent),
    day: date = Query(...),
    db: Session = Depends(get_db),
):
    """
    Get or generate daily narrative.
    
    Requires: Authentication + valid consent (data analysis scope)
    """
    repo = NarrativeRepository(db)
    obj = repo.get_for_period(user_id=user_id, period_type="daily", period_start=day, period_end=day)
    if obj:
        return _to_schema(obj)
    obj = generate_and_persist_narrative(db, user_id=user_id, period_type="daily", start=day, end=day)
    return _to_schema(obj)


@router.get("/weekly", response_model=NarrativeResponse)
def get_weekly_narrative(
    user_id: int = Depends(require_user_and_consent),
    week_start: date = Query(..., description="Monday (recommended)"),
    db: Session = Depends(get_db),
):
    """
    Get or generate weekly narrative.
    
    Requires: Authentication + valid consent (data analysis scope)
    """
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
    user_id: int = Depends(require_user_and_consent),
    db: Session = Depends(get_db)
):
    """
    Generate a narrative for user.
    
    Requires: Authentication + valid consent (data analysis scope)
    """
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
    user_id: int = Depends(require_user_and_consent),
    period_type: str = Query("daily"),
    limit: int = Query(14, ge=1, le=100),
    db: Session = Depends(get_db),
):
    repo = NarrativeRepository(db)
    items = repo.list_recent(user_id=user_id, period_type=period_type, limit=limit)
    return {"count": len(items), "items": [_to_schema(x) for x in items]}


def _to_schema(obj) -> NarrativeResponse:
    # Normalize JSON fields to expected names
    drivers = obj.drivers_json or []
    actions = obj.actions_json or []
    risks = obj.risks_json or []
    metadata = obj.metadata_json or {}

    # Backward-compatible enrichment: attach domain_key to segments if missing.
    # PURE METADATA ONLY (no reordering, no suppression, no wording changes).
    def _enrich(segs):
        out = []
        for s in segs:
            if not isinstance(s, dict):
                out.append(s)
                continue
            if s.get("domain_key") is None:
                mk = s.get("metric_key")
                dk = domain_for_signal(mk) if isinstance(mk, str) else None
                s = dict(s)
                s["domain_key"] = dk.value if dk else None
            out.append(s)
        return out

    drivers = _enrich(drivers)
    actions = _enrich(actions)
    risks = _enrich(risks)

    # Key points are strings for backward compatibility; store structured segments in metadata.
    if isinstance(metadata, dict) and "key_point_segments" not in metadata:
        kp_segments = []
        for kp in (obj.key_points_json or []):
            if not isinstance(kp, str):
                continue
            mk = kp.split(":", 1)[0].strip() if ":" in kp else None
            dk = domain_for_signal(mk) if mk else None
            kp_segments.append({"text": kp, "metric_key": mk, "domain_key": dk.value if dk else None})
        metadata = dict(metadata)
        metadata["key_point_segments"] = kp_segments

    return NarrativeResponse(
        id=obj.id,
        user_id=obj.user_id,
        period_type=obj.period_type,
        period_start=obj.period_start,
        period_end=obj.period_end,
        title=obj.title,
        summary=obj.summary,
        key_points=obj.key_points_json or [],
        drivers=drivers,
        actions=actions,
        risks=risks,
        metadata=metadata,
        created_at=obj.created_at,
    )

