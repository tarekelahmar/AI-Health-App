from datetime import datetime, timedelta
from statistics import mean, pstdev
from sqlalchemy.orm import Session
import logging

from app.domain.metric_registry import get_metric_spec, METRICS
from app.domain.models.baseline import Baseline
from app.domain.models.health_data_point import HealthDataPoint
from app.engine.baseline_errors import BaselineError, BaselineErrorType, BaselineUnavailable
from typing import Union

logger = logging.getLogger(__name__)


def recompute_baseline(
    *,
    db: Session,
    user_id: int,
    metric_key: str,
    window_days: int = 30,
) -> Baseline:
    """
    Simple, robust baseline:
    - take last N days
    - mean + population stddev (pstdev)
    
    SECURITY FIX (Risk #5): Never silently fail. Raise BaselineUnavailable with typed error.
    """
    # Validate metric exists
    try:
        get_metric_spec(metric_key)
    except (ValueError, KeyError) as e:
        error = BaselineError(
            error_type=BaselineErrorType.METRIC_NOT_FOUND,
            message=f"Metric '{metric_key}' not found in registry: {e}",
            user_id=user_id,
            metric_key=metric_key,
            recoverable=False,
        )
        logger.error(
            "baseline_computation_failed",
            extra={
                "error_type": error.error_type.value,
                "user_id": user_id,
                "metric_key": metric_key,
                "message": error.message,
            },
        )
        raise BaselineUnavailable(error)

    since = datetime.utcnow() - timedelta(days=window_days)

    try:
        rows = (
            db.query(HealthDataPoint)
            .filter(
                HealthDataPoint.user_id == user_id,
                HealthDataPoint.metric_type == metric_key,
                HealthDataPoint.timestamp >= since,
            )
            .order_by(HealthDataPoint.timestamp.asc())
            .all()
        )
    except Exception as e:
        error = BaselineError(
            error_type=BaselineErrorType.DATABASE_ERROR,
            message=f"Database query failed: {e}",
            user_id=user_id,
            metric_key=metric_key,
            recoverable=True,
        )
        logger.error(
            "baseline_computation_failed",
            extra={
                "error_type": error.error_type.value,
                "user_id": user_id,
                "metric_key": metric_key,
                "message": error.message,
            },
        )
        raise BaselineUnavailable(error)

    values = [r.value for r in rows if r.value is not None]
    
    # SECURITY FIX: Explicit insufficient data handling
    if len(values) < 5:
        error = BaselineError(
            error_type=BaselineErrorType.INSUFFICIENT_DATA,
            message=f"Insufficient data for baseline: {len(values)} < 5 points required",
            user_id=user_id,
            metric_key=metric_key,
            recoverable=True,  # Can retry when more data arrives
        )
        logger.warning(
            "baseline_insufficient_data",
            extra={
                "error_type": error.error_type.value,
                "user_id": user_id,
                "metric_key": metric_key,
                "n_points": len(values),
            },
        )
        raise BaselineUnavailable(error)
    
    try:
        mu = mean(values)
        sd = pstdev(values) if len(values) > 1 else 0.0
    except Exception as e:
        error = BaselineError(
            error_type=BaselineErrorType.COMPUTATION_ERROR,
            message=f"Statistical computation failed: {e}",
            user_id=user_id,
            metric_key=metric_key,
            recoverable=False,
        )
        logger.error(
            "baseline_computation_failed",
            extra={
                "error_type": error.error_type.value,
                "user_id": user_id,
                "metric_key": metric_key,
                "message": error.message,
            },
        )
        raise BaselineUnavailable(error)

    try:
        baseline = (
            db.query(Baseline)
            .filter(Baseline.user_id == user_id, Baseline.metric_type == metric_key)
            .one_or_none()
        )

        if baseline is None:
            baseline = Baseline(
                user_id=user_id,
                metric_type=metric_key,
                mean=mu,
                std=sd,
                window_days=window_days,
            )
            db.add(baseline)
        else:
            baseline.mean = mu
            baseline.std = sd
            baseline.window_days = window_days

        db.commit()
        db.refresh(baseline)
        return baseline
    except Exception as e:
        # SECURITY FIX: Never silently fail - raise typed error
        error = BaselineError(
            error_type=BaselineErrorType.TABLE_MISSING if "does not exist" in str(e).lower() else BaselineErrorType.DATABASE_ERROR,
            message=f"Baseline persistence failed: {e}",
            user_id=user_id,
            metric_key=metric_key,
            recoverable=True,  # May be recoverable if table is created
        )
        logger.error(
            "baseline_persistence_failed",
            extra={
                "error_type": error.error_type.value,
                "user_id": user_id,
                "metric_key": metric_key,
                "message": error.message,
            },
        )
        raise BaselineUnavailable(error)


def compute_baselines_for_user(
    db: Session,
    user_id: int,
    window_days: int = 30,
) -> dict:
    """
    Compute baselines for all registered metrics for a user.
    
    Returns dict with:
    - computed: list of metric keys successfully computed
    - failed: list of (metric_key, error_type) tuples for failures
    - skipped: list of metric keys skipped (insufficient data, etc.)
    """
    computed = []
    failed = []
    skipped = []
    
    for metric_key in METRICS.keys():
        try:
            recompute_baseline(
                db=db,
                user_id=user_id,
                metric_key=metric_key,
                window_days=window_days,
            )
            computed.append(metric_key)
        except BaselineUnavailable as e:
            if e.error.error_type == BaselineErrorType.INSUFFICIENT_DATA:
                skipped.append(metric_key)
            else:
                failed.append((metric_key, e.error.error_type.value))
        except Exception as e:
            # Unexpected error
            logger.error(
                "baseline_computation_unexpected_error",
                extra={
                    "user_id": user_id,
                    "metric_key": metric_key,
                    "error": str(e),
                },
            )
            failed.append((metric_key, "unexpected_error"))
    
    return {
        "computed": computed,
        "failed": failed,
        "skipped": skipped,
    }
