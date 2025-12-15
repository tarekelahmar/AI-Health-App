from __future__ import annotations

from datetime import datetime

from typing import Optional

from sqlalchemy import String, Integer, DateTime, Boolean, Text

from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AdherenceEvent(Base):
    __tablename__ = "adherence_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(Integer, index=True)
    experiment_id: Mapped[int] = mapped_column(Integer, index=True)
    intervention_id: Mapped[int] = mapped_column(Integer, index=True)

    taken: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    dose: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dose_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

