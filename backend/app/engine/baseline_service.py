from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging
from typing import Union, Literal

from app.domain.metrics.registry import get_metric_spec, METRIC_REGISTRY as METRICS
from app.domain.models.baseline import Baseline
from app.domain.models.health_data_point import HealthDataPoint
from app.engine.baseline_errors import BaselineError, BaselineErrorType, BaselineUnavailable
from app.engine.statistics.robust_baseline import estimate_baseline

logger = logging.getLogger(__name__)

# Default estimation method for new baselines
DEFAULT_ESTIMATION_METHOD: Literal["median_mad", "trimmed_mean", "huber", "simple_mean"] = "median_mad"


def recompute_baseline(
    *,
    db: Session,
    user_id: int,
    metric_key: str,
    window_days: int = 30,
    method: str = "median_mad",
) -> Baseline:
    """
    Compute a robust baseline for a metric using outlier-resistant estimators.

    Phase 2.1: Uses median/MAD by default instead of mean/std.
    Stores confidence intervals and sample metadata for auditability.

    Raises BaselineUnavailable with typed error on any failure.
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

    if len(values) < 5:
        error = BaselineError(
            error_type=BaselineErrorType.INSUFFICIENT_DATA,
            message=f"Insufficient data for baseline: {len(values)} < 5 points required",
            user_id=user_id,
            metric_key=metric_key,
            recoverable=True,
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
        estimate = estimate_baseline(values, method=method, min_samples=5)
        if estimate is None:
            raise ValueError("estimate_baseline returned None despite sufficient data")
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
                mean=estimate.center,
                std=estimate.spread,
                window_days=window_days,
                method=estimate.method,
                n_samples=estimate.n_samples,
                ci_80_low=estimate.ci_80[0],
                ci_80_high=estimate.ci_80[1],
                ci_95_low=estimate.ci_95[0],
                ci_95_high=estimate.ci_95[1],
                is_stable=estimate.is_stable,
            )
            db.add(baseline)
        else:
            baseline.mean = estimate.center
            baseline.std = estimate.spread
            baseline.window_days = window_days
            baseline.method = estimate.method
            baseline.n_samples = estimate.n_samples
            baseline.ci_80_low = estimate.ci_80[0]
            baseline.ci_80_high = estimate.ci_80[1]
            baseline.ci_95_low = estimate.ci_95[0]
            baseline.ci_95_high = estimate.ci_95[1]
            baseline.is_stable = estimate.is_stable

        db.commit()
        db.refresh(baseline)
        return baseline
    except Exception as e:
        error = BaselineError(
            error_type=BaselineErrorType.TABLE_MISSING if "does not exist" in str(e).lower() else BaselineErrorType.DATABASE_ERROR,
            message=f"Baseline persistence failed: {e}",
            user_id=user_id,
            metric_key=metric_key,
            recoverable=True,
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
    method: str = "median_mad",
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
                method=method,
            )
            computed.append(metric_key)
        except BaselineUnavailable as e:
            if e.error.error_type == BaselineErrorType.INSUFFICIENT_DATA:
                skipped.append(metric_key)
            else:
                failed.append((metric_key, e.error.error_type.value))
        except Exception as e:
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
