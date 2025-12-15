from __future__ import annotations

from fastapi import APIRouter

from app.api.public_router import public_router
from app.api.schemas.safety import SafetyDecisionOut, SafetyEvaluateRequest
from app.engine.safety.safety_service import SafetyService

router = public_router(prefix="/api/v1/safety", tags=["safety"])


@router.post("/evaluate", response_model=SafetyDecisionOut)
def evaluate(req: SafetyEvaluateRequest) -> SafetyDecisionOut:
    decision = SafetyService.evaluate_intervention(
        intervention_key=req.intervention_key,
        user_flags=req.user_flags,
        requested_boundary=req.requested_boundary,
        requested_evidence=req.requested_evidence,
    )
    return SafetyDecisionOut(**decision.to_dict())

