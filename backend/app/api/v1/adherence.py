from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.api.router_factory import make_v1_router
from app.api.auth_mode import get_request_user_id

from app.api.schemas.adherence import AdherenceLog, AdherenceOut

from app.core.database import get_db

from app.domain.models.adherence_event import AdherenceEvent

from app.domain.repositories.adherence_repository import AdherenceRepository

# SECURITY: Changed from public_router to make_v1_router - adherence contains PHI
router: APIRouter = make_v1_router(prefix="/api/v1/adherence", tags=["adherence"])


@router.post("/log", response_model=AdherenceOut)
def log_adherence(
    payload: AdherenceLog,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    # SECURITY: Override payload.user_id with authenticated user_id
    repo = AdherenceRepository(db)
    data = payload.model_dump()
    data["user_id"] = user_id  # Use authenticated user_id, not payload.user_id
    if data.get("timestamp") is None:
        data["timestamp"] = datetime.utcnow()
    event = AdherenceEvent(**data)
    return repo.create(event)


@router.get("", response_model=list[AdherenceOut])
def list_adherence(
    experiment_id: int,
    user_id: int = Depends(get_request_user_id),
    limit: int = 500,
    db: Session = Depends(get_db)
):
    """
    List adherence events for an experiment.
    
    SECURITY FIX (Week 1): Verify experiment ownership before returning adherence data.
    """
    from app.domain.repositories.experiment_repository import ExperimentRepository
    
    # SECURITY FIX: Verify experiment ownership
    exp_repo = ExperimentRepository(db)
    exp = exp_repo.get(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    if exp.user_id != user_id:
        raise HTTPException(status_code=403, detail="Cannot view adherence: experiment belongs to another user")
    
    repo = AdherenceRepository(db)
    return repo.list_by_experiment_and_user(experiment_id=experiment_id, user_id=user_id, limit=limit)

