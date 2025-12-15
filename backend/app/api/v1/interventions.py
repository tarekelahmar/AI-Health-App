import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.schemas.interventions import InterventionCreate, InterventionResponse
from app.domain.repositories.intervention_repository import InterventionRepository
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/api/v1/interventions", tags=["interventions"])

@router.post("", response_model=InterventionResponse)
def create_intervention(
    payload: InterventionCreate,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    # SECURITY: Override payload.user_id with authenticated user_id
    repo = InterventionRepository(db)
    try:
        row = repo.create_with_safety(
            user_id=user_id,  # Use authenticated user_id, not payload.user_id
            key=payload.key,
            name=payload.name,
            category=payload.category,
            dosage=payload.dosage,
            schedule=payload.schedule,
            notes=payload.notes,
            user_flags=payload.user_flags or {},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Expand JSON issues into list for response model
    try:
        issues = json.loads(row.safety_issues_json or "[]")
    except Exception:
        issues = []

    return InterventionResponse(
        id=row.id,
        user_id=row.user_id,
        key=row.key,
        name=row.name,
        category=row.category,
        dosage=row.dosage,
        schedule=row.schedule,
        notes=row.notes,
        safety_risk_level=row.safety_risk_level,
        safety_evidence_grade=row.safety_evidence_grade,
        safety_boundary=row.safety_boundary,
        safety_issues=issues,
        safety_notes=row.safety_notes,
    )

@router.get("", response_model=list[InterventionResponse])
def list_interventions(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    repo = InterventionRepository(db)
    rows = repo.list_by_user(user_id=user_id)
    out: list[InterventionResponse] = []
    for row in rows:
        try:
            issues = json.loads(row.safety_issues_json or "[]")
        except Exception:
            issues = []
        out.append(
            InterventionResponse(
                id=row.id,
                user_id=row.user_id,
                key=row.key,
                name=row.name,
                category=row.category,
                dosage=row.dosage,
                schedule=row.schedule,
                notes=row.notes,
                safety_risk_level=row.safety_risk_level,
                safety_evidence_grade=row.safety_evidence_grade,
                safety_boundary=row.safety_boundary,
                safety_issues=issues,
                safety_notes=row.safety_notes,
            )
        )
    return out
