from __future__ import annotations

from datetime import datetime

from typing import Optional, Dict, Any

from sqlalchemy import String, Integer, DateTime, Float, Text, JSON

from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(Integer, index=True)
    experiment_id: Mapped[int] = mapped_column(Integer, index=True)

    metric_key: Mapped[str] = mapped_column(String(100), nullable=False)

    verdict: Mapped[str] = mapped_column(String(30), nullable=False)  # helpful|unclear|not_helpful|insufficient_data

    summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Baseline stats
    baseline_mean: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_std: Mapped[float] = mapped_column(Float, nullable=False)

    # Intervention stats
    intervention_mean: Mapped[float] = mapped_column(Float, nullable=False)
    intervention_std: Mapped[float] = mapped_column(Float, nullable=False)

    # Effect metrics
    delta: Mapped[float] = mapped_column(Float, nullable=False)
    percent_change: Mapped[float] = mapped_column(Float, nullable=False)
    effect_size: Mapped[float] = mapped_column(Float, nullable=False)

    # Quality metrics
    coverage: Mapped[float] = mapped_column(Float, nullable=False)  # 0..1
    adherence_rate: Mapped[float] = mapped_column(Float, nullable=False)  # 0..1

    # Legacy fields (for backward compatibility)
    pre_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    post_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    data_coverage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0..1
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0..1

    # Structured details (JSON)
    details_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

