from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.api.public_router import public_router

from app.api.schemas.adherence import AdherenceLog, AdherenceOut

from app.core.database import get_db

from app.domain.models.adherence_event import AdherenceEvent

from app.domain.repositories.adherence_repository import AdherenceRepository

router: APIRouter = public_router(prefix="/api/v1/adherence", tags=["adherence"])


@router.post("/log", response_model=AdherenceOut)
def log_adherence(payload: AdherenceLog, db: Session = Depends(get_db)):
    repo = AdherenceRepository(db)
    data = payload.model_dump()
    if data.get("timestamp") is None:
        data["timestamp"] = datetime.utcnow()
    event = AdherenceEvent(**data)
    return repo.create(event)


@router.get("", response_model=list[AdherenceOut])
def list_adherence(experiment_id: int, limit: int = 500, db: Session = Depends(get_db)):
    repo = AdherenceRepository(db)
    return repo.list_by_experiment(experiment_id=experiment_id, limit=limit)

