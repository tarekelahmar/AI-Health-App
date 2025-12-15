from __future__ import annotations

from datetime import datetime

from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text

from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(Integer, index=True)

    # Link to intervention / protocol (optional protocol for MVP)
    intervention_id: Mapped[int] = mapped_column(Integer, index=True)
    protocol_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)

    # Hypothesis & primary target
    hypothesis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    primary_metric_key: Mapped[str] = mapped_column(String(100), index=True)  # e.g. sleep_duration_min
    expected_direction: Mapped[str] = mapped_column(String(20), nullable=False)  # up|down|stable

    baseline_window_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    intervention_window_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active|stopped|completed

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

