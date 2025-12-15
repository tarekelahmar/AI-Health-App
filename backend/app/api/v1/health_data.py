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

    # SECURITY FIX (Risk #6): Import unit conversion service
    from app.domain.unit_conversion import (
        validate_unit_compatibility,
        convert_unit,
        UnitConversionError,
    )
    from datetime import timezone
    
    for p in payload.points:
        try:
            spec = get_metric_spec(p.metric_key)
        except ValueError as e:
            rejected += 1
            reasons.append(str(e))
            continue

        # SECURITY FIX (Risk #6): Validate and convert units
        provided_unit = p.unit or spec.unit  # Default to canonical if not provided
        canonical_unit = spec.unit
        
        # Validate unit compatibility
        is_compatible, error_msg, _ = validate_unit_compatibility(
            provided_unit=provided_unit,
            expected_unit=canonical_unit,
            metric_key=p.metric_key,
        )
        
        if not is_compatible:
            rejected += 1
            reasons.append(error_msg or f"{p.metric_key}: unit '{provided_unit}' incompatible with expected '{canonical_unit}'")
            continue
        
        # Convert value if units differ
        value = p.value
        if provided_unit.lower() != canonical_unit.lower():
            try:
                value = convert_unit(
                    value=p.value,
                    from_unit=provided_unit,
                    to_unit=canonical_unit,
                )
            except UnitConversionError as e:
                rejected += 1
                reasons.append(f"{p.metric_key}: unit conversion failed: {e}")
                continue

        # Range checks (soft reject)
        if spec.min_value is not None and value < spec.min_value:
            rejected += 1
            reasons.append(f"{p.metric_key}: value below min ({value} < {spec.min_value})")
            continue
        if spec.max_value is not None and value > spec.max_value:
            rejected += 1
            reasons.append(f"{p.metric_key}: value above max ({value} > {spec.max_value})")
            continue

        # SECURITY FIX (Risk #6): Make timestamp timezone-aware (store as UTC)
        timestamp = p.timestamp
        if timestamp.tzinfo is None:
            # Assume UTC if timezone-naive
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC if timezone-aware
            timestamp = timestamp.astimezone(timezone.utc)
        # Remove timezone for database storage (SQLAlchemy DateTime doesn't handle timezone well)
        timestamp = timestamp.replace(tzinfo=None)

        row = HealthDataPoint(
            user_id=payload.user_id,
            metric_type=p.metric_key,
            value=value,  # Use converted value
            unit=canonical_unit,  # Always store canonical unit
            timestamp=timestamp,
            source=p.source,
        )
        db.add(row)
        inserted += 1
        touched_metrics.add(p.metric_key)

    db.commit()

    # Recompute baseline for touched metrics (MVP)
    # SECURITY FIX (Risk #5): Handle baseline errors explicitly
    from app.engine.baseline_errors import BaselineUnavailable
    for mk in touched_metrics:
        try:
            recompute_baseline(db=db, user_id=payload.user_id, metric_key=mk, window_days=30)
        except BaselineUnavailable as e:
            # Log but don't fail the entire batch - baseline can be recomputed later
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "baseline_recompute_skipped",
                extra={
                    "user_id": payload.user_id,
                    "metric_key": mk,
                    "error_type": e.error.error_type.value,
                    "recoverable": e.error.recoverable,
                },
            )

    return HealthDataBatchOut(inserted=inserted, rejected=rejected, rejected_reasons=reasons)
