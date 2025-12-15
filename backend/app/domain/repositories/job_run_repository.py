"""Repository for job run tracking."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.domain.models.job_run import JobRun, JobRunStatus


class JobRunRepository:
    """Repository for job run tracking."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        job_id: str,
        idempotency_key: str,
        metadata: Optional[dict] = None,
    ) -> JobRun:
        """Create a new job run record."""
        import json
        job_run = JobRun(
            job_id=job_id,
            idempotency_key=idempotency_key,
            status=JobRunStatus.PENDING,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        self.db.add(job_run)
        self.db.commit()
        self.db.refresh(job_run)
        return job_run
    
    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[JobRun]:
        """Get job run by idempotency key."""
        return (
            self.db.query(JobRun)
            .filter(JobRun.idempotency_key == idempotency_key)
            .first()
        )
    
    def mark_running(self, job_run_id: int) -> JobRun:
        """Mark job as running."""
        job_run = self.db.query(JobRun).filter(JobRun.id == job_run_id).first()
        if job_run:
            job_run.status = JobRunStatus.RUNNING
            job_run.started_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(job_run)
        return job_run
    
    def mark_completed(
        self,
        job_run_id: int,
        result_summary: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> JobRun:
        """Mark job as completed."""
        import json
        job_run = self.db.query(JobRun).filter(JobRun.id == job_run_id).first()
        if job_run:
            job_run.status = JobRunStatus.COMPLETED
            job_run.completed_at = datetime.utcnow()
            if job_run.started_at:
                duration = (job_run.completed_at - job_run.started_at).total_seconds()
                job_run.duration_seconds = int(duration)
            if result_summary:
                job_run.result_summary = result_summary
            if metadata:
                job_run.metadata_json = json.dumps(metadata)
            self.db.commit()
            self.db.refresh(job_run)
        return job_run
    
    def mark_failed(
        self,
        job_run_id: int,
        error_message: str,
        metadata: Optional[dict] = None,
    ) -> JobRun:
        """Mark job as failed."""
        import json
        job_run = self.db.query(JobRun).filter(JobRun.id == job_run_id).first()
        if job_run:
            job_run.status = JobRunStatus.FAILED
            job_run.completed_at = datetime.utcnow()
            if job_run.started_at:
                duration = (job_run.completed_at - job_run.started_at).total_seconds()
                job_run.duration_seconds = int(duration)
            job_run.error_message = error_message
            if metadata:
                job_run.metadata_json = json.dumps(metadata)
            self.db.commit()
            self.db.refresh(job_run)
        return job_run
    
    def mark_skipped(self, job_run_id: int, reason: str) -> JobRun:
        """Mark job as skipped (e.g., duplicate execution)."""
        job_run = self.db.query(JobRun).filter(JobRun.id == job_run_id).first()
        if job_run:
            job_run.status = JobRunStatus.SKIPPED
            job_run.result_summary = reason
            self.db.commit()
            self.db.refresh(job_run)
        return job_run
    
    def list_recent(
        self,
        job_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[JobRun]:
        """List recent job runs."""
        q = self.db.query(JobRun)
        if job_id:
            q = q.filter(JobRun.job_id == job_id)
        return (
            q.order_by(desc(JobRun.created_at))
            .limit(limit)
            .all()
        )
    
    def check_recent_completion(
        self,
        job_id: str,
        idempotency_key: str,
        within_seconds: int = 3600,  # 1 hour default
    ) -> Optional[JobRun]:
        """
        Check if a job with the same idempotency key completed recently.
        
        Returns the recent job run if found, None otherwise.
        """
        recent = datetime.utcnow() - timedelta(seconds=within_seconds)
        return (
            self.db.query(JobRun)
            .filter(
                JobRun.job_id == job_id,
                JobRun.idempotency_key == idempotency_key,
                JobRun.status == JobRunStatus.COMPLETED,
                JobRun.completed_at >= recent,
            )
            .first()
        )

