import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.schemas.protocols import ProtocolCreate, ProtocolResponse
from app.domain.repositories.protocol_repository import ProtocolRepository
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/api/v1/protocols", tags=["protocols"])

@router.post("", response_model=ProtocolResponse)
def create_protocol(
    payload: ProtocolCreate,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    # SECURITY: Override payload.user_id with authenticated user_id
    repo = ProtocolRepository(db)
    row = repo.create_with_safety_summary(
        user_id=user_id,  # Use authenticated user_id, not payload.user_id
        title=payload.title,
        description=payload.description,
        interventions=payload.interventions or [],
    )
    try:
        interventions = json.loads(row.interventions_json or "[]")
    except Exception:
        interventions = []
    try:
        safety_summary = json.loads(row.safety_summary_json or "{}")
    except Exception:
        safety_summary = {}
    return ProtocolResponse(
        id=row.id,
        user_id=row.user_id,
        title=row.title,
        description=row.description,
        status=row.status,
        version=row.version,
        interventions=interventions,
        safety_summary=safety_summary,
    )

@router.get("", response_model=list[ProtocolResponse])
def list_protocols(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    repo = ProtocolRepository(db)
    rows = repo.list_by_user(user_id=user_id)
    out: list[ProtocolResponse] = []
    for row in rows:
        try:
            interventions = json.loads(row.interventions_json or "[]")
        except Exception:
            interventions = []
        try:
            safety_summary = json.loads(row.safety_summary_json or "{}")
        except Exception:
            safety_summary = {}
        out.append(
            ProtocolResponse(
                id=row.id,
                user_id=row.user_id,
                title=row.title,
                description=row.description,
                status=row.status,
                version=row.version,
                interventions=interventions,
                safety_summary=safety_summary,
            )
        )
    return out
