"""Repository for audit events."""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.domain.models.audit_event import AuditEvent


class AuditRepository:
    """Repository for audit events."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        *,
        user_id: int,
        entity_type: str,
        entity_id: int,
        decision_type: str,
        decision_reason: Optional[str] = None,
        source_metrics: Optional[List[str]] = None,
        time_windows: Optional[Dict[str, Dict[str, Any]]] = None,
        detectors_used: Optional[List[str]] = None,
        thresholds_crossed: Optional[List[Dict[str, Any]]] = None,
        safety_checks_applied: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Create an audit event."""
        import json
        
        event = AuditEvent(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            decision_type=decision_type,
            decision_reason=decision_reason,
            source_metrics=json.dumps(source_metrics) if source_metrics else None,
            time_windows=json.dumps(time_windows) if time_windows else None,
            detectors_used=json.dumps(detectors_used) if detectors_used else None,
            thresholds_crossed=json.dumps(thresholds_crossed) if thresholds_crossed else None,
            safety_checks_applied=json.dumps(safety_checks_applied) if safety_checks_applied else None,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
    
    def list_for_entity(
        self,
        *,
        user_id: int,
        entity_type: str,
        entity_id: int,
        limit: int = 50,
    ) -> List[AuditEvent]:
        """List audit events for a specific entity."""
        return (
            self.db.query(AuditEvent)
            .filter(
                AuditEvent.user_id == user_id,
                AuditEvent.entity_type == entity_type,
                AuditEvent.entity_id == entity_id,
            )
            .order_by(desc(AuditEvent.created_at))
            .limit(limit)
            .all()
        )
    
    def list_for_user(
        self,
        *,
        user_id: int,
        entity_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """List audit events for a user."""
        q = self.db.query(AuditEvent).filter(AuditEvent.user_id == user_id)
        if entity_type:
            q = q.filter(AuditEvent.entity_type == entity_type)
        return (
            q.order_by(desc(AuditEvent.created_at))
            .limit(limit)
            .all()
        )

