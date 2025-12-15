"""Metrics endpoints"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.domain.models.health_data_point import HealthDataPoint
from app.domain.models.baseline import Baseline as BaselineModel
from app.api.schemas.metrics import MetricSeriesResponse, MetricPoint, MetricBaseline
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/series", response_model=MetricSeriesResponse)
def get_metric_series(
    user_id: int = Depends(get_request_user_id),
    metric_key: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Get metric series data with baseline.
    Returns points and baseline for visualization.
    """
    
    # Get data points (using metric_type - the Python attribute mapped to data_type column)
    points = (
        db.query(HealthDataPoint)
        .filter(
            HealthDataPoint.user_id == user_id,
            HealthDataPoint.metric_type == metric_key,
        )
        .order_by(HealthDataPoint.timestamp.asc())
        .all()
    )
    
    # Convert to response format
    metric_points = [
        MetricPoint(
            timestamp=point.timestamp.isoformat(),
            value=point.value,
        )
        for point in points
    ]
    
    # Get baseline directly from model (handle missing table gracefully)
    try:
        baseline_model = (
            db.query(BaselineModel)
            .filter(
                BaselineModel.user_id == user_id,
                BaselineModel.metric_type == metric_key,
            )
            .one_or_none()
        )
        
        if baseline_model:
            baseline = MetricBaseline(
                mean=baseline_model.mean,
                std=baseline_model.std,
            )
        else:
            # Return zero baseline if not found
            baseline = MetricBaseline(mean=0.0, std=0.0)
    except Exception as e:
        # WEEK 4: Log error instead of silently ignoring
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "baseline_query_failed",
            extra={
                "user_id": user_id,
                "metric_key": metric_key,
                "error": str(e),
            },
        )
        # If baselines table doesn't exist, return zero baseline
        baseline = MetricBaseline(mean=0.0, std=0.0)
    
    return MetricSeriesResponse(
        metric_key=metric_key,
        points=metric_points,
        baseline=baseline,
    )
