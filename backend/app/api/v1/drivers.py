from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.schemas.drivers import (
    DriverFindingOut,
    DriversResponse,
    GenerateDriversRequest,
    PersonalDriverOut,
    PersonalDriversResponse,
    TopDriversResponse,
)
from app.domain.repositories.driver_finding_repository import DriverFindingRepository
from app.domain.repositories.personal_driver_repository import PersonalDriverRepository
from app.engine.drivers.driver_discovery_service import DriverDiscoveryService
from app.engine.attribution.cross_signal_engine import CrossSignalAttributionEngine
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
import json

router = make_v1_router(prefix="/api/v1/drivers", tags=["drivers"])


def _to_schema(finding) -> DriverFindingOut:
    """Convert DriverFinding model to schema"""
    import logging
    logger = logging.getLogger(__name__)
    
    details = None
    if finding.details_json:
        try:
            details = json.loads(finding.details_json)
        except Exception as e:
            # WEEK 4: Log error instead of silently ignoring
            logger.warning(
                "driver_finding_json_parse_failed",
                extra={
                    "finding_id": finding.id,
                    "error": str(e),
                },
            )
            details = {}
    
    return DriverFindingOut(
        id=finding.id,
        user_id=finding.user_id,
        exposure_type=finding.exposure_type,
        exposure_key=finding.exposure_key,
        metric_key=finding.metric_key,
        lag_days=finding.lag_days,
        direction=finding.direction,
        effect_size=finding.effect_size,
        confidence=finding.confidence,
        coverage=finding.coverage,
        n_exposure_days=finding.n_exposure_days,
        n_total_days=finding.n_total_days,
        window_start=finding.window_start,
        window_end=finding.window_end,
        details=details,
        created_at=finding.created_at,
    )


@router.get("/recent", response_model=DriversResponse)
def get_recent_drivers(
    user_id: int = Depends(get_request_user_id),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get recent driver findings for a user"""
    repo = DriverFindingRepository(db)
    findings = repo.list_recent(user_id=user_id, limit=limit)
    return DriversResponse(
        count=len(findings),
        items=[_to_schema(f) for f in findings],
    )


@router.get("/by-metric", response_model=DriversResponse)
def get_drivers_by_metric(
    user_id: int = Depends(get_request_user_id),
    metric_key: str = Query(...),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get driver findings for a specific metric"""
    repo = DriverFindingRepository(db)
    findings = repo.list_by_metric(user_id=user_id, metric_key=metric_key, limit=limit)
    return DriversResponse(
        count=len(findings),
        items=[_to_schema(f) for f in findings],
    )


@router.post("/generate", response_model=DriversResponse)
def generate_drivers(
    payload: GenerateDriversRequest,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """
    Run driver discovery for a user.
    
    Analyzes associations between behaviors/interventions and metrics.
    Returns top findings sorted by confidence * effect_size.
    """
    service = DriverDiscoveryService(db)
    findings = service.discover_drivers(
        user_id=user_id,
        window_days=payload.window_days,
        max_findings=payload.max_findings,
    )
    return DriversResponse(
        count=len(findings),
        items=[_to_schema(f) for f in findings],
    )


# Personal Drivers endpoints
@router.get("/personal", response_model=PersonalDriversResponse)
def get_personal_drivers(
    user_id: int = Depends(get_request_user_id),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get personal drivers for a user (ranked)"""
    repo = PersonalDriverRepository(db)
    drivers = repo.list_for_user(user_id=user_id, limit=limit)
    return PersonalDriversResponse(
        count=len(drivers),
        items=[PersonalDriverOut.model_validate(d) for d in drivers],
    )


@router.get("/top", response_model=TopDriversResponse)
def get_top_drivers(
    user_id: int = Depends(get_request_user_id),
    outcome_metric: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get top positive and negative drivers for an outcome"""
    repo = PersonalDriverRepository(db)
    positive = repo.get_top_positive(user_id=user_id, outcome_metric=outcome_metric, limit=limit)
    negative = repo.get_top_negative(user_id=user_id, outcome_metric=outcome_metric, limit=limit)
    return TopDriversResponse(
        outcome_metric=outcome_metric,
        positive=[PersonalDriverOut.model_validate(d) for d in positive],
        negative=[PersonalDriverOut.model_validate(d) for d in negative],
    )


@router.post("/recompute", response_model=PersonalDriversResponse)
def recompute_personal_drivers(
    user_id: int = Depends(get_request_user_id),
    window_days: int = Query(28, ge=7, le=365),
    db: Session = Depends(get_db),
):
    """
    Recompute personal drivers for a user.
    
    Runs cross-signal attribution engine.
    """
    engine = CrossSignalAttributionEngine(db)
    drivers = engine.compute_personal_drivers(
        user_id=user_id,
        window_days=window_days,
    )
    return PersonalDriversResponse(
        count=len(drivers),
        items=[PersonalDriverOut.model_validate(d) for d in drivers],
    )

