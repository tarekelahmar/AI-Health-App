"""
Job run tracking for idempotency and observability.

SECURITY FIX (Risk #10): Tracks job executions to prevent duplicates
and enable migration to worker-based scheduler.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Text, Index, Enum as SQLEnum
from enum import Enum as PyEnum
from app.core.database import Base


class JobRunStatus(str, PyEnum):
    """Job run status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # Skipped due to idempotency check


class JobRun(Base):
    """Tracks job executions for idempotency and observability."""
    __tablename__ = "job_runs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), nullable=False, index=True)  # e.g., "recompute_baselines"
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)  # Unique key for idempotency
    
    status = Column(SQLEnum(JobRunStatus), nullable=False, default=JobRunStatus.PENDING, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    error_message = Column(Text, nullable=True)
    result_summary = Column(Text, nullable=True)  # Human-readable summary
    
    # Structured metadata (JSON)
    metadata_json = Column(Text, nullable=True)  # Job-specific details
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_job_runs_job_status", "job_id", "status"),
        Index("ix_job_runs_created", "created_at"),
    )

