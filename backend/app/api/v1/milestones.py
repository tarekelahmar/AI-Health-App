"""Milestones + Synthesis API endpoints."""

import json
from typing import List, Optional

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.core.database import get_db

router = make_v1_router(prefix="/api/v1/journal", tags=["journal"])


# ── Schemas ───────────────────────────────────────────────────────

class MilestoneResponse(BaseModel):
    id: int
    milestone_type: str
    detected_date: str
    description: str
    category: str
    metadata_json: Optional[dict] = None

    class Config:
        from_attributes = True


class SynthesisResponse(BaseModel):
    """Generic synthesis response (weekly or monthly)."""
    data: dict


# ── Milestones ────────────────────────────────────────────────────

@router.get("/milestones", response_model=List[MilestoneResponse])
def get_milestones(
    user_id: int = Depends(get_request_user_id),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get recent milestones for the user."""
    from app.engine.milestone_detector import get_user_milestones
    rows = get_user_milestones(db, user_id, limit)
    results = []
    for r in rows:
        meta = None
        if r.metadata_json:
            try:
                meta = json.loads(r.metadata_json) if isinstance(r.metadata_json, str) else r.metadata_json
            except (json.JSONDecodeError, TypeError):
                meta = None
        results.append(MilestoneResponse(
            id=r.id,
            milestone_type=r.milestone_type,
            detected_date=str(r.detected_date),
            description=r.description,
            category=r.category,
            metadata_json=meta,
        ))
    return results


# ── Synthesis ─────────────────────────────────────────────────────

@router.get("/synthesis/weekly", response_model=SynthesisResponse)
def get_weekly_synthesis(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Generate weekly synthesis for the last 7 days."""
    from app.engine.journal_synthesis import generate_weekly_synthesis
    result = generate_weekly_synthesis(db, user_id)
    if result is None:
        return SynthesisResponse(data={})
    return SynthesisResponse(data=result.to_dict())


@router.get("/synthesis/monthly", response_model=SynthesisResponse)
def get_monthly_synthesis(
    month: str = Query(None, description="Month in YYYY-MM format"),
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Generate monthly synthesis."""
    from app.engine.journal_synthesis import generate_monthly_synthesis
    result = generate_monthly_synthesis(db, user_id, month_str=month)
    if result is None:
        return SynthesisResponse(data={})
    return SynthesisResponse(data=result.to_dict())
