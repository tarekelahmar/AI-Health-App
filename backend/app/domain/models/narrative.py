from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class Narrative(Base):
    __tablename__ = "narratives"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)

    # Period this narrative covers
    period_type = Column(String(20), nullable=False)  # "daily" | "weekly" (extensible)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Human-readable story
    title = Column(String(255), nullable=False, default="Your health summary")
    summary = Column(Text, nullable=False, default="")

    # Structured content for UI
    key_points_json = Column(JSONB, nullable=False, default=list)   # list[str] or list[dict]
    drivers_json = Column(JSONB, nullable=False, default=list)      # list[{metric_key, why, evidence}]
    actions_json = Column(JSONB, nullable=False, default=list)      # list[{action, rationale, safety}]
    risks_json = Column(JSONB, nullable=False, default=list)        # list[{risk, guidance}]
    metadata_json = Column(JSONB, nullable=False, default=dict)     # any extra (counts, coverage, etc.)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_pinned = Column(Boolean, nullable=False, default=False)


Index("ix_narratives_user_period", Narrative.user_id, Narrative.period_type, Narrative.period_start, Narrative.period_end, unique=False)

