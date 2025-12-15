from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app.api.schemas.experiments import ExperimentStart, ExperimentStop, ExperimentOut
from app.domain.repositories.experiment_repository import ExperimentRepository
from app.domain.repositories.intervention_repository import InterventionRepository
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

# SECURITY FIX (Week 1): Use make_v1_router to enforce auth
router = make_v1_router(prefix="/api/v1/experiments", tags=["experiments"])


@router.post("/start", response_model=ExperimentOut)
def start_experiment(
    payload: ExperimentStart,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db)
):
    """
    Start a new experiment.
    
    SECURITY FIX (Week 1): Override payload.user_id with authenticated user_id to prevent spoofing.
    """
    repo = ExperimentRepository(db)
    # (K3) Enforce that experiment cannot start on a blocked/high-risk intervention boundary.
    # MVP rule: if the referenced intervention is HIGH risk => block experiment start.
    if payload.intervention_id:
        irepo = InterventionRepository(db)
        row = irepo.get(payload.intervention_id)
        # SECURITY FIX: Also check ownership of intervention
        if row and row.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot start experiment: intervention belongs to another user.",
            )
        if row and (row.safety_risk_level == "high"):
            raise HTTPException(
                status_code=400,
                detail="Cannot start experiment: intervention is HIGH risk / blocked by safety policy.",
            )
    
    # SECURITY FIX: Override payload.user_id with authenticated user_id
    exp_data = payload.model_dump()
    exp_data["user_id"] = user_id  # Use authenticated user_id, not payload.user_id
    
    from app.domain.models.experiment import Experiment
    exp = Experiment(**exp_data)
    return repo.create(exp)


@router.post("/{experiment_id}/stop", response_model=ExperimentOut)
def stop_experiment(
    experiment_id: int,
    payload: ExperimentStop,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db)
):
    """
    Stop an experiment.
    
    SECURITY FIX (Week 1): Verify ownership before allowing stop.
    """
    repo = ExperimentRepository(db)
    exp = repo.get(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # SECURITY FIX: Verify ownership
    if exp.user_id != user_id:
        raise HTTPException(status_code=403, detail="Cannot stop experiment: belongs to another user")
    
    ended_at = payload.ended_at or datetime.utcnow()
    updated = repo.stop(experiment_id=experiment_id, status=payload.status, ended_at=ended_at)
    if not updated:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return updated


@router.get("", response_model=list[ExperimentOut])
def list_experiments(
    user_id: int = Depends(get_request_user_id),
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List experiments for the authenticated user.
    
    SECURITY FIX (Week 1): user_id now comes from authenticated request, not query parameter.
    """
    repo = ExperimentRepository(db)
    return repo.list_by_user(user_id=user_id, limit=limit)


# -----------------------------
# Step E2: evaluation endpoint
# Step H3+H4: attribution-aware evaluation
# -----------------------------
from fastapi import Body
import json
from app.api.schemas.evaluations import EvaluateExperimentRequest, EvaluationResultResponse
from app.engine.evaluation_service import evaluate_experiment as _evaluate_experiment
from app.domain.repositories.health_data_repository import HealthDataRepository
from app.domain.repositories.adherence_repository import AdherenceRepository
from app.domain.repositories.insight_repository import InsightRepository
from app.domain.repositories.evaluation_repository import EvaluationRepository
from app.engine.attribution.lagged_effects import LaggedEffectEngine
from app.engine.attribution.attribution_to_insight import build_attribution_insight_domain_fields


@router.post("/{experiment_id}/evaluate", response_model=EvaluationResultResponse)
def evaluate_experiment_endpoint(
    experiment_id: int,
    payload: EvaluateExperimentRequest = Body(default=EvaluateExperimentRequest()),
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """
    Evaluate an experiment.
    
    SECURITY FIX (Week 1): Verify ownership before allowing evaluation.
    """
    # Get experiment to access metric_key and user_id
    exp_repo = ExperimentRepository(db)
    exp = exp_repo.get(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # SECURITY FIX: Verify ownership
    if exp.user_id != user_id:
        raise HTTPException(status_code=403, detail="Cannot evaluate experiment: belongs to another user")
    
    metric_key = exp.primary_metric_key
    
    # 1) Run your existing evaluation engine (already built in Step E2)
    ev = _evaluate_experiment(
        db=db,
        experiment_id=experiment_id,
        baseline_days=payload.baseline_days,
        intervention_days=payload.intervention_days,
        min_coverage=payload.min_coverage,
        min_points=payload.min_points,
    )
    
    # 2) Run lagged attribution engine (Step H1)
    health_repo = HealthDataRepository(db)
    adherence_repo = AdherenceRepository(db)
    
    lag_engine = LaggedEffectEngine(
        health_repo=health_repo,
        experiment_repo=exp_repo,
        adherence_repo=adherence_repo,
    )
    
    attributions = lag_engine.run(
        experiment_id=experiment_id,
        metric_key=metric_key,
        baseline_days=payload.baseline_days,
    )
    
    # 3) Enrich evaluation.details_json with attribution summary (best lag)
    # details_json can be dict or json-string; normalize to dict
    details = {}
    details_raw = getattr(ev, "details_json", None)
    if isinstance(details_raw, str) and details_raw.strip():
        try:
            details = json.loads(details_raw)
        except Exception:
            details = {}
    elif isinstance(details_raw, dict):
        details = details_raw
    
    # Best attribution (if available)
    best_attr = None
    if attributions:
        best_attr = sorted(attributions, key=lambda a: abs(a.effect_size) * a.confidence, reverse=True)[0]
        details["attribution"] = {
            "metric_key": best_attr.metric_key,
            "direction": best_attr.direction,
            "effect_size": best_attr.effect_size,
            "confidence": best_attr.confidence,
            "coverage": best_attr.coverage,
            "best_lag_days": best_attr.lag_days,
        }
    else:
        details["attribution"] = None
    
    # WEEK 4: Write back details_json with explicit error handling
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        ev.details_json = json.dumps(details) if isinstance(details, dict) else details
        db.commit()
        db.refresh(ev)
    except Exception as e:
        # WEEK 4: Log error but don't fail entire evaluation
        logger.warning(
            "evaluation_details_update_failed",
            extra={
                "user_id": user_id,
                "experiment_id": experiment_id,
                "evaluation_id": ev.id,
                "error": str(e),
            },
        )
        # Continue - evaluation is still valid without details update
    
    # 4) Create an "attribution" insight so it shows up in the feed (H3)
    try:
        insight_repo = InsightRepository(db)
        insight_fields = build_attribution_insight_domain_fields(
            user_id=exp.user_id,
            attributions=attributions,
            experiment_id=experiment_id,
            intervention_id=exp.intervention_id,
            metric_key=metric_key,
        )
        insight_repo.create(**insight_fields)
    except Exception as e:
        # WEEK 4: Log error but don't fail entire evaluation
        logger.warning(
            "attribution_insight_creation_failed",
            extra={
                "user_id": user_id,
                "experiment_id": experiment_id,
                "evaluation_id": ev.id,
                "error": str(e),
            },
        )
        # Continue - evaluation is still valid without attribution insight
    
    return EvaluationResultResponse(
        id=ev.id,
        user_id=ev.user_id,
        experiment_id=ev.experiment_id,
        metric_key=ev.metric_key,
        baseline_mean=ev.baseline_mean,
        baseline_std=ev.baseline_std,
        intervention_mean=ev.intervention_mean,
        intervention_std=ev.intervention_std,
        delta=ev.delta,
        percent_change=ev.percent_change,
        effect_size=ev.effect_size,
        coverage=float(ev.coverage or 0.0),
        adherence_rate=float(ev.adherence_rate or 0.0),
        verdict=ev.verdict,
        created_at=ev.created_at,
        details=ev.details_json if isinstance(ev.details_json, dict) else (json.loads(ev.details_json) if isinstance(ev.details_json, str) else {}),
    )

