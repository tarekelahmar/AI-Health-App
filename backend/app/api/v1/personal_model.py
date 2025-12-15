from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.domain.repositories.personal_health_model_repository import PersonalHealthModelRepository

router = make_v1_router(prefix="/api/v1/personal-model", tags=["personal-model"])


@router.get("")
def get_personal_model(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Get user's personal health model - stable representations of their health patterns"""
    repo = PersonalHealthModelRepository(db)
    model = repo.get_or_create(user_id)
    
    return {
        "id": model.id,
        "user_id": model.user_id,
        "baselines": model.baselines_json or {},
        "sensitivities": model.sensitivities_json or {},
        "drivers": model.drivers_json or {},
        "response_patterns": model.response_patterns_json or {},
        "confidence_score": model.confidence_score,
        "data_coverage": model.data_coverage,
        "model_version": model.model_version,
        "updated_at": model.updated_at.isoformat() if model.updated_at else None,
    }

