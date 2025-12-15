"""
X6: Performance & Cost Guardrails

Implement limits and metrics to prevent runaway compute and monitor system efficiency.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.domain.models.insight import Insight
from app.domain.models.evaluation_result import EvaluationResult
from app.domain.models.narrative import Narrative

logger = logging.getLogger(__name__)


@dataclass
class PerformanceLimits:
    """Performance limits configuration."""
    max_insights_per_user_per_day: int = 50
    max_experiments_per_metric: int = 3
    max_attribution_lag_window_days: int = 7
    max_batch_size_ingestion: int = 1000
    max_loop_runtime_ms: int = 5000  # 5 seconds
    max_narrative_generation_time_ms: int = 3000  # 3 seconds


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    loop_runtime_ms: float
    insights_per_user: int
    evaluations_per_day: int
    narrative_generation_time_ms: float
    batch_ingestion_size: int
    attribution_lag_window_days: int


# Default limits
DEFAULT_LIMITS = PerformanceLimits()


def check_insights_per_user_limit(
    db: Session,
    user_id: int,
    limit: int = DEFAULT_LIMITS.max_insights_per_user_per_day,
) -> tuple[bool, Optional[str]]:
    """
    Check if user has exceeded daily insight limit.
    
    Returns (is_within_limit, error_message).
    """
    today = datetime.utcnow().date()
    start_of_day = datetime.combine(today, datetime.min.time())
    
    count = (
        db.query(func.count(Insight.id))
        .filter(
            and_(
                Insight.user_id == user_id,
                Insight.generated_at >= start_of_day,
            )
        )
        .scalar()
    )
    
    if count >= limit:
        return False, f"Daily insight limit exceeded: {count} >= {limit}"
    
    return True, None


def check_experiments_per_metric_limit(
    db: Session,
    user_id: int,
    metric_key: str,
    limit: int = DEFAULT_LIMITS.max_experiments_per_metric,
) -> tuple[bool, Optional[str]]:
    """
    Check if user has exceeded experiments per metric limit.
    
    Returns (is_within_limit, error_message).
    """
    from app.domain.models.experiment import Experiment
    
    count = (
        db.query(func.count(Experiment.id))
        .filter(
            and_(
                Experiment.user_id == user_id,
                Experiment.metric_key == metric_key,
            )
        )
        .scalar()
    )
    
    if count >= limit:
        return False, f"Experiments per metric limit exceeded for {metric_key}: {count} >= {limit}"
    
    return True, None


def check_attribution_lag_window(
    lag_days: int,
    max_lag: int = DEFAULT_LIMITS.max_attribution_lag_window_days,
) -> tuple[bool, Optional[str]]:
    """
    Check if attribution lag window is within limits.
    
    Returns (is_within_limit, error_message).
    """
    if lag_days > max_lag:
        return False, f"Attribution lag window too large: {lag_days} > {max_lag}"
    
    return True, None


def check_batch_size(
    batch_size: int,
    max_size: int = DEFAULT_LIMITS.max_batch_size_ingestion,
) -> tuple[bool, Optional[str]]:
    """
    Check if batch size is within limits.
    
    Returns (is_within_limit, error_message).
    """
    if batch_size > max_size:
        return False, f"Batch size too large: {batch_size} > {max_size}"
    
    return True, None


def measure_loop_runtime(func):
    """Decorator to measure loop runtime."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        runtime_ms = (time.time() - start_time) * 1000
        
        if runtime_ms > DEFAULT_LIMITS.max_loop_runtime_ms:
            logger.warning(
                f"Loop runtime exceeded limit: {runtime_ms:.2f}ms > {DEFAULT_LIMITS.max_loop_runtime_ms}ms",
                extra={
                    "runtime_ms": runtime_ms,
                    "limit_ms": DEFAULT_LIMITS.max_loop_runtime_ms,
                },
            )
        
        return result
    return wrapper


def measure_narrative_generation_time(func):
    """Decorator to measure narrative generation time."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        runtime_ms = (time.time() - start_time) * 1000
        
        if runtime_ms > DEFAULT_LIMITS.max_narrative_generation_time_ms:
            logger.warning(
                f"Narrative generation time exceeded limit: {runtime_ms:.2f}ms > {DEFAULT_LIMITS.max_narrative_generation_time_ms}ms",
                extra={
                    "runtime_ms": runtime_ms,
                    "limit_ms": DEFAULT_LIMITS.max_narrative_generation_time_ms,
                },
            )
        
        return result
    return wrapper


def get_performance_metrics(
    db: Session,
    user_id: int,
    window_days: int = 1,
) -> PerformanceMetrics:
    """
    Get performance metrics for a user over a time window.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=window_days)
    
    # Insights per user
    insights_count = (
        db.query(func.count(Insight.id))
        .filter(
            and_(
                Insight.user_id == user_id,
                Insight.generated_at >= start_date,
            )
        )
        .scalar()
    )
    
    # Evaluations per day
    evaluations_count = (
        db.query(func.count(EvaluationResult.id))
        .filter(
            and_(
                EvaluationResult.user_id == user_id,
                EvaluationResult.created_at >= start_date,
            )
        )
        .scalar()
    )
    
    # Note: loop_runtime_ms and narrative_generation_time_ms would need to be
    # tracked separately (e.g., in a metrics table or via decorators)
    # For now, return defaults
    
    return PerformanceMetrics(
        loop_runtime_ms=0.0,  # Would be tracked separately
        insights_per_user=insights_count or 0,
        evaluations_per_day=evaluations_count or 0,
        narrative_generation_time_ms=0.0,  # Would be tracked separately
        batch_ingestion_size=0,  # Would be tracked separately
        attribution_lag_window_days=0,  # Would be tracked separately
    )


def check_performance_limits(
    db: Session,
    user_id: int,
    metric_key: Optional[str] = None,
    batch_size: Optional[int] = None,
    lag_days: Optional[int] = None,
    limits: Optional[PerformanceLimits] = None,
) -> tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Check all performance limits.
    
    Returns (is_within_limits, error_message, metadata).
    """
    if limits is None:
        limits = DEFAULT_LIMITS
    
    metadata: Dict[str, Any] = {}
    
    # Check insights limit
    is_ok, error = check_insights_per_user_limit(db, user_id, limits.max_insights_per_user_per_day)
    if not is_ok:
        return False, error, metadata
    
    # Check experiments limit (if metric_key provided)
    if metric_key:
        is_ok, error = check_experiments_per_metric_limit(db, user_id, metric_key, limits.max_experiments_per_metric)
        if not is_ok:
            return False, error, metadata
    
    # Check batch size (if provided)
    if batch_size:
        is_ok, error = check_batch_size(batch_size, limits.max_batch_size_ingestion)
        if not is_ok:
            return False, error, metadata
    
    # Check lag window (if provided)
    if lag_days:
        is_ok, error = check_attribution_lag_window(lag_days, limits.max_attribution_lag_window_days)
        if not is_ok:
            return False, error, metadata
    
    return True, None, metadata

