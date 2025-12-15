from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.api.schemas.health_data import HealthDataBatchIn, HealthDataBatchOut
from app.domain.metric_registry import get_metric_spec
from app.domain.models.health_data_point import HealthDataPoint
from app.engine.baseline_service import recompute_baseline
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/api/v1/health-data", tags=["health-data"])


@router.post("/batch", response_model=HealthDataBatchOut)
def ingest_health_data_batch(
    payload: HealthDataBatchIn,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db)
):
    # Override payload.user_id with authenticated user_id (prevent spoofing)
    payload.user_id = user_id
    
    inserted = 0
    rejected = 0
    reasons: list[str] = []

    # Group metrics touched, recompute baselines once per metric
    touched_metrics: set[str] = set()

    for p in payload.points:
        try:
            spec = get_metric_spec(p.metric_key)
        except ValueError as e:
            rejected += 1
            reasons.append(str(e))
            continue

        # Unit normalization: for MVP enforce registry unit
        unit = spec.unit

        # Range checks (soft reject)
        if spec.min_value is not None and p.value < spec.min_value:
            rejected += 1
            reasons.append(f"{p.metric_key}: value below min ({p.value} < {spec.min_value})")
            continue
        if spec.max_value is not None and p.value > spec.max_value:
            rejected += 1
            reasons.append(f"{p.metric_key}: value above max ({p.value} > {spec.max_value})")
            continue

        row = HealthDataPoint(
            user_id=payload.user_id,
            metric_type=p.metric_key,
            value=p.value,
            unit=unit,
            timestamp=p.timestamp,
            source=p.source,
        )
        db.add(row)
        inserted += 1
        touched_metrics.add(p.metric_key)

    db.commit()

    # Recompute baseline for touched metrics (MVP)
    for mk in touched_metrics:
        recompute_baseline(db=db, user_id=payload.user_id, metric_key=mk, window_days=30)

    return HealthDataBatchOut(inserted=inserted, rejected=rejected, rejected_reasons=reasons)
