from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index, JSON

from app.core.database import Base


class DataProvenance(Base):
    """
    Tracks where every data point came from.
    
    Core principle: No data enters the model loop unless it is:
    - validated
    - provenance-tagged
    - quality-scored
    - reversible (can be excluded later)
    """
    __tablename__ = "data_provenance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)

    source_type = Column(String(50), nullable=False)  # "wearable", "lab", "manual", "questionnaire"
    source_name = Column(String(100), nullable=False)  # "whoop", "oura", "labcorp", "user"
    source_record_id = Column(String(255), nullable=True)  # External record ID (e.g., WHOOP sleep ID)

    ingestion_run_id = Column(String(100), nullable=False)  # Unique ID for this ingestion batch
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    is_validated = Column(Boolean, nullable=False, default=False)
    # Using JSON instead of JSONB for SQLite compatibility in tests
    validation_errors = Column(JSON, nullable=True)  # List of validation errors if any

    # Quality metadata
    quality_score = Column(JSON, nullable=True)  # Full quality score breakdown

    __table_args__ = (
        Index("ix_data_provenance_user_run", "user_id", "ingestion_run_id"),
        Index("ix_data_provenance_source", "source_type", "source_name"),
    )

