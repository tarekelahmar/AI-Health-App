"""API endpoints for audit trail."""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.schemas.audit import AuditEventOut, AuditEventsResponse
from app.domain.repositories.audit_repository import AuditRepository
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/api/v1/audit", tags=["audit"])


def _to_schema(event) -> AuditEventOut:
    """Convert AuditEvent model to schema."""
    import json
    
    source_metrics = None
    if event.source_metrics:
        try:
            source_metrics = json.loads(event.source_metrics)
        except Exception:
            pass
    
    time_windows = None
    if event.time_windows:
        try:
            time_windows = json.loads(event.time_windows)
        except Exception:
            pass
    
    detectors_used = None
    if event.detectors_used:
        try:
            detectors_used = json.loads(event.detectors_used)
        except Exception:
            pass
    
    thresholds_crossed = None
    if event.thresholds_crossed:
        try:
            thresholds_crossed = json.loads(event.thresholds_crossed)
        except Exception:
            pass
    
    safety_checks_applied = None
    if event.safety_checks_applied:
        try:
            safety_checks_applied = json.loads(event.safety_checks_applied)
        except Exception:
            pass
    
    metadata = None
    if event.metadata_json:
        try:
            metadata = json.loads(event.metadata_json)
        except Exception:
            pass
    
    return AuditEventOut(
        id=event.id,
        user_id=event.user_id,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        decision_type=event.decision_type,
        decision_reason=event.decision_reason,
        source_metrics=source_metrics,
        time_windows=time_windows,
        detectors_used=detectors_used,
        thresholds_crossed=thresholds_crossed,
        safety_checks_applied=safety_checks_applied,
        metadata=metadata,
        created_at=event.created_at,
    )


@router.get("/entity", response_model=AuditEventsResponse)
def get_audit_for_entity(
    user_id: int = Depends(get_request_user_id),
    entity_type: str = Query(...),
    entity_id: int = Query(...),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get audit trail for a specific entity (insight, protocol, evaluation, narrative)."""
    repo = AuditRepository(db)
    events = repo.list_for_entity(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )
    return AuditEventsResponse(
        count=len(events),
        items=[_to_schema(e) for e in events],
    )


@router.get("/", response_model=AuditEventsResponse)
def list_audit_events(
    user_id: int = Depends(get_request_user_id),
    entity_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List audit events for a user."""
    repo = AuditRepository(db)
    events = repo.list_for_user(
        user_id=user_id,
        entity_type=entity_type,
        limit=limit,
    )
    return AuditEventsResponse(
        count=len(events),
        items=[_to_schema(e) for e in events],
    )

