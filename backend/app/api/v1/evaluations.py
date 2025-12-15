from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.api.schemas.evaluations import EvaluationResultResponse

from app.domain.models.evaluation_result import EvaluationResult

router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"], dependencies=[])


@router.get("", response_model=list[EvaluationResultResponse])
def list_evaluations(
    user_id: int = Query(..., ge=1),
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
                verdict=r.verdict,
                created_at=r.created_at,
                details=r.details_json or {},
            )
        )
    return out

