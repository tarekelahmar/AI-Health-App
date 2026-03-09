"""
Personal Pattern Model - Phase 3.2

Stores detected patterns in a user's health data with lifecycle tracking.
Patterns progress through: hypothesis → confirmed → disproven/deprecated.

Examples:
- Correlation: "Late caffeine correlates with lower HRV next morning"
- Trigger: "Alcohol > 2 drinks triggers sleep quality drop"
- Cycle: "Energy peaks on Monday, dips on Thursday"
- Response: "Magnesium improves sleep within 2 days"
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, JSON, Boolean, Index,
)

from app.core.database import Base


class PersonalPattern(Base):
    """
    A detected pattern in a user's health data.

    Lifecycle: hypothesis → confirmed → disproven/deprecated
    """
    __tablename__ = "personal_patterns"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)

    # Pattern type
    pattern_type = Column(String(30), nullable=False)  # correlation | trigger | cycle | response

    # What signals are involved
    input_signals_json = Column(JSON, nullable=False)  # ["late_caffeine", "alcohol"]
    output_signal = Column(String(100), nullable=False)  # "hrv_rmssd"

    # Relationship details (varies by type)
    # For correlation: {"r": 0.72, "p_value": 0.001, "direction": "negative"}
    # For trigger: {"threshold": 2, "unit": "drinks", "effect_size": -0.8}
    # For cycle: {"period_days": 7, "phase": "peak_monday"}
    # For response: {"lag_hours": 48, "effect_size": 0.6}
    relationship_json = Column(JSON, nullable=True)

    # Confidence tracking
    times_observed = Column(Integer, nullable=False, default=1)
    times_confirmed = Column(Integer, nullable=False, default=0)
    current_confidence = Column(Float, nullable=False, default=0.3)

    # Temporal aspects
    first_detected = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_confirmed = Column(DateTime, nullable=True)
    typical_lag_hours = Column(Float, nullable=True)

    # Status lifecycle
    status = Column(String(20), nullable=False, default="hypothesis")  # hypothesis | confirmed | disproven | deprecated

    # User interaction
    user_acknowledged = Column(Boolean, nullable=False, default=False)
    user_notes = Column(Text, nullable=True)

    # Provenance
    source_insight_ids_json = Column(JSON, nullable=True)  # Which insights led to this pattern

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_personal_pattern_user_type", "user_id", "pattern_type"),
        Index("ix_personal_pattern_user_status", "user_id", "status"),
        Index("ix_personal_pattern_user_output", "user_id", "output_signal"),
    )
