from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.api.schemas.evaluations import EvaluationResultResponse

from app.domain.models.evaluation_result import EvaluationResult
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/api/v1/evaluations", tags=["evaluations"])


@router.get("", response_model=list[EvaluationResultResponse])
def list_evaluations(
    user_id: int = Depends(get_request_user_id),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(EvaluationResult)
        .filter(EvaluationResult.user_id == user_id)
        .order_by(EvaluationResult.created_at.desc())
        .limit(limit)
        .all()
    )

    out: List[EvaluationResultResponse] = []
    for r in rows:
        # SECURITY FIX (Risk #7): Extract confidence and adherence evidence from details
        details = r.details_json or {}
        confidence_score = details.get("confidence_score")
        has_adherence_evidence = details.get("has_adherence_evidence", float(r.adherence_rate or 0.0) > 0.0)
        
        out.append(
            EvaluationResultResponse(
                id=r.id,
                user_id=r.user_id,
                experiment_id=r.experiment_id,
                metric_key=r.metric_key,
                baseline_mean=r.baseline_mean,
                baseline_std=r.baseline_std,
                intervention_mean=r.intervention_mean,
                intervention_std=r.intervention_std,
                delta=r.delta,
                percent_change=r.percent_change,
                effect_size=r.effect_size,
                coverage=float(r.coverage or 0.0),
                adherence_rate=float(r.adherence_rate or 0.0),
                confidence_score=confidence_score,
                has_adherence_evidence=has_adherence_evidence,
                verdict=r.verdict,
                created_at=r.created_at,
                details=details,
            )
        )
    return out

