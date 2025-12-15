"""API schemas for audit events."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    """Audit event response schema."""
    id: int
    user_id: int
    entity_type: str
    entity_id: int
    decision_type: str
    decision_reason: Optional[str] = None
    source_metrics: Optional[List[str]] = None
    time_windows: Optional[Dict[str, Dict[str, Any]]] = None
    detectors_used: Optional[List[str]] = None
    thresholds_crossed: Optional[List[Dict[str, Any]]] = None
    safety_checks_applied: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditEventsResponse(BaseModel):
    """Response for list of audit events."""
    count: int
    items: List[AuditEventOut]

