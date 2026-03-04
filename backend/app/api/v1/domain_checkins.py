"""
Domain Check-ins API — weekly explicit life domain ratings.

Endpoints:
- GET  /api/v1/domain-checkins/status  — check if a domain check-in is due
- POST /api/v1/domain-checkins         — submit 5 domain ratings
- GET  /api/v1/domain-checkins/history — get past check-in history
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.engine.domain_checkin_service import (
    get_domain_checkin_status,
    save_domain_checkin,
    get_domain_checkin_history,
)

router = make_v1_router(prefix="/api/v1/domain-checkins", tags=["domain-checkins"])


# ── Schemas ──────────────────────────────────────────────────────

class DomainCheckinRequest(BaseModel):
    session_id: Optional[int] = None
    career: float = Field(..., ge=1.0, le=10.0)
    relationship: float = Field(..., ge=1.0, le=10.0)
    social: float = Field(..., ge=1.0, le=10.0)
    health: float = Field(..., ge=1.0, le=10.0)
    finance: float = Field(..., ge=1.0, le=10.0)


class DomainCheckinStatusResponse(BaseModel):
    due: bool
    last_checkin_date: Optional[str] = None
    days_since: Optional[int] = None


class DomainCheckinResponse(BaseModel):
    id: int
    checkin_date: str
    career: float
    relationship: float
    social: float
    health: float
    finance: float


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/status", response_model=DomainCheckinStatusResponse)
def check_status(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Check whether a weekly domain check-in is due."""
    result = get_domain_checkin_status(db, user_id)
    return DomainCheckinStatusResponse(**result)


@router.post("", response_model=DomainCheckinResponse)
def submit_checkin(
    body: DomainCheckinRequest,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Submit a weekly domain check-in with 5 domain ratings."""
    scores = {
        "career": body.career,
        "relationship": body.relationship,
        "social": body.social,
        "health": body.health,
        "finance": body.finance,
    }
    checkin = save_domain_checkin(db, user_id, body.session_id, scores)
    db.commit()

    return DomainCheckinResponse(
        id=checkin.id,
        checkin_date=checkin.checkin_date,
        career=checkin.career,
        relationship=checkin.relationship,
        social=checkin.social,
        health=checkin.health,
        finance=checkin.finance,
    )


@router.get("/history", response_model=List[DomainCheckinResponse])
def checkin_history(
    weeks: int = Query(default=12, ge=1, le=52),
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Get domain check-in history."""
    return get_domain_checkin_history(db, user_id, weeks=weeks)
