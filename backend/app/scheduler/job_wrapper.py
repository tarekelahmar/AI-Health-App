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


def generate_idempotency_key(job_id: str, **kwargs) -> str:
    """
    Generate idempotency key from job_id and parameters.
    
    Args:
        job_id: Job identifier
        **kwargs: Job parameters (will be serialized into key)
    
    Returns:
        Unique idempotency key
    """
    # Sort kwargs for consistent hashing
    params_str = ",".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_str = f"{job_id}:{params_str}:{datetime.utcnow().date().isoformat()}"
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
                # Generate idempotency key
                idempotency_key = generate_idempotency_key(job_id, **kwargs)
                
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
                
                # Create job run record
                job_run = repo.create(
                    job_id=job_id,
                    idempotency_key=idempotency_key,
                    metadata={"args": str(args), "kwargs": kwargs},
                )
                
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

