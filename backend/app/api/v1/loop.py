from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.domain.models.evaluation_result import EvaluationResult

from app.domain.models.loop_decision import LoopDecision

from app.domain.repositories.loop_decision_repository import LoopDecisionRepository

from app.domain.repositories.evaluation_repository import EvaluationRepository
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

from app.engine.loop_orchestrator import decide_next_step

# SECURITY FIX (Week 1): Use make_v1_router to enforce auth
router = make_v1_router(prefix="/api/v1/loop", tags=["loop"])


@router.post("/run/{evaluation_id}")
def run_loop_decision(
    evaluation_id: int,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db)
):
    """
    Run loop decision for an evaluation.
    
    SECURITY FIX (Week 1): Verify ownership before allowing loop decision.
    """
    # Direct lookup by evaluation_id
    evaluation = db.query(EvaluationResult).filter(EvaluationResult.id == evaluation_id).first()
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    # SECURITY FIX: Verify ownership
    if evaluation.user_id != user_id:
        raise HTTPException(status_code=403, detail="Cannot run loop decision: evaluation belongs to another user")

    decision_dict = decide_next_step(evaluation=evaluation)

    decision_repo = LoopDecisionRepository(db)
    decision = decision_repo.create(
        LoopDecision(
            user_id=evaluation.user_id,
            experiment_id=evaluation.experiment_id,
            evaluation_id=evaluation.id,
            action=decision_dict["action"],
            reason=decision_dict["reason"],
            metadata_json=decision_dict["metadata_json"],
        )
    )

    return {
        "decision_id": decision.id,
        "action": decision.action,
        "reason": decision.reason,
        "metadata": decision.metadata_json,
    }

