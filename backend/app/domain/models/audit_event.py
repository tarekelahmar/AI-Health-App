"""
X4: User-Visible Audit Trail

Stores comprehensive logging of system decisions and their underlying data/logic for explainability.
For every Insight, Protocol, Evaluation, and Narrative, store source metrics, time windows,
detectors used, thresholds crossed, and safety checks applied.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from app.core.database import Base


class AuditEvent(Base):
    """Audit trail for system decisions."""
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    
    # What was created/decided
    entity_type = Column(String(50), nullable=False)  # "insight", "protocol", "evaluation", "narrative", "intervention"
    entity_id = Column(Integer, nullable=False)  # ID of the entity
    
    # Decision metadata
    decision_type = Column(String(50), nullable=False)  # "created", "updated", "suppressed", "escalated"
    decision_reason = Column(String(200), nullable=True)  # Human-readable reason
    
    # Source data
    source_metrics = Column(Text, nullable=True)  # JSON array of metric keys used
    time_windows = Column(Text, nullable=True)  # JSON dict of window_start/end per metric
    detectors_used = Column(Text, nullable=True)  # JSON array of detector names
    thresholds_crossed = Column(Text, nullable=True)  # JSON array of threshold names/values
    safety_checks_applied = Column(Text, nullable=True)  # JSON array of safety check results
    
    # Additional context
    metadata_json = Column(Text, nullable=True)  # JSON for flexible additional context
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("ix_audit_events_user_entity", "user_id", "entity_type", "entity_id"),
        Index("ix_audit_events_created_at", "created_at"),
    )

