"""
Job wrapper for idempotency and observability.

SECURITY FIX (Risk #10): Wraps jobs with idempotency checks and run tracking.
"""

from __future__ import annotations

import logging
import hashlib
from datetime import datetime
from typing import Callable, Optional, Dict, Any
from functools import wraps

from app.core.database import SessionLocal
from app.domain.repositories.job_run_repository import JobRunRepository, JobRunStatus

logger = logging.getLogger(__name__)


def generate_idempotency_key(job_id: str, idempotency_window_seconds: int = 3600, **kwargs) -> str:
    """
    Generate idempotency key from job_id and parameters.
    
    AUDIT FIX: Include time bucket to allow multiple runs per day.
    Uses time bucket (window_seconds) instead of date-only to prevent uniqueness violations.
    
    Args:
        job_id: Job identifier
        idempotency_window_seconds: Time window for idempotency (used for bucketing)
        **kwargs: Job parameters (will be serialized into key)
    
    Returns:
        Unique idempotency key (includes time bucket)
    """
    from datetime import timedelta
    
    # AUDIT FIX: Use time bucket instead of date-only
    # Bucket time into windows (e.g., if window is 1 hour, bucket by hour)
    now = datetime.utcnow()
    # Calculate which bucket this time falls into
    bucket_seconds = (now.timestamp() // idempotency_window_seconds) * idempotency_window_seconds
    bucket_time = datetime.fromtimestamp(bucket_seconds)
    
    # Sort kwargs for consistent hashing
    params_str = ",".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    # Include bucket time instead of just date
    key_str = f"{job_id}:{params_str}:{bucket_time.isoformat()}"
    return hashlib.sha256(key_str.encode()).hexdigest()


def with_idempotency(
    job_id: str,
    idempotency_window_seconds: int = 3600,  # 1 hour default
):
    """
    Decorator to add idempotency and observability to job functions.
    
    SECURITY FIX (Risk #10): Prevents duplicate job execution within time window.
    
    Usage:
        @with_idempotency("my_job", idempotency_window_seconds=7200)
        def my_job_function():
            # Job logic here
            return {"result": "success"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            db = SessionLocal()
            try:
                # AUDIT FIX: Generate idempotency key with time bucket
                idempotency_key = generate_idempotency_key(
                    job_id, 
                    idempotency_window_seconds=idempotency_window_seconds,
                    **kwargs
                )
                
                # Check if job already completed recently
                repo = JobRunRepository(db)
                recent_run = repo.check_recent_completion(
                    job_id=job_id,
                    idempotency_key=idempotency_key,
                    within_seconds=idempotency_window_seconds,
                )
                
                if recent_run:
                    logger.info(
                        f"Job {job_id} skipped (idempotency): completed at {recent_run.completed_at}"
                    )
                    return {
                        "status": "skipped",
                        "reason": "idempotency_check",
                        "previous_run_id": recent_run.id,
                        "previous_completed_at": recent_run.completed_at.isoformat(),
                    }
                
                # AUDIT FIX: Handle uniqueness violations gracefully
                # Create job run record - catch uniqueness constraint violations
                try:
                    job_run = repo.create(
                        job_id=job_id,
                        idempotency_key=idempotency_key,
                        metadata={"args": str(args), "kwargs": kwargs},
                    )
                except Exception as create_error:
                    # If uniqueness violation, check if another process already created it
                    error_str = str(create_error).lower()
                    if "unique" in error_str or "duplicate" in error_str:
                        # Another process may have created it - check again
                        existing = (
                            db.query(repo.model)
                            .filter(repo.model.idempotency_key == idempotency_key)
                            .first()
                        )
                        if existing:
                            logger.info(
                                f"Job {job_id} skipped (concurrent execution): another process already running"
                            )
                            return {
                                "status": "skipped",
                                "reason": "concurrent_execution",
                                "existing_run_id": existing.id,
                            }
                    # Re-raise if it's a different error
                    raise
                
                # Mark as running
                repo.mark_running(job_run.id)
                
                try:
                    # Execute job
                    result = func(*args, **kwargs)
                    
                    # Mark as completed
                    result_summary = str(result) if result else "completed"
                    repo.mark_completed(
                        job_run_id=job_run.id,
                        result_summary=result_summary[:500],  # Truncate long summaries
                        metadata={"result": result} if isinstance(result, dict) else None,
                    )
                    
                    logger.info(f"Job {job_id} completed successfully (run_id={job_run.id})")
                    return result
                    
                except Exception as e:
                    # Mark as failed
                    error_msg = str(e)
                    repo.mark_failed(
                        job_run_id=job_run.id,
                        error_message=error_msg[:1000],  # Truncate long errors
                        metadata={"exception_type": type(e).__name__},
                    )
                    logger.error(f"Job {job_id} failed (run_id={job_run.id}): {e}")
                    raise
                    
            finally:
                db.close()
        
        return wrapper
    return decorator

