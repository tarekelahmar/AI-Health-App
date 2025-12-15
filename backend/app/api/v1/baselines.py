from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.engine.baseline_service import recompute_baseline
from app.engine.baseline_errors import BaselineUnavailable
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/baselines", tags=["baselines"])


class BaselineRecomputeIn(BaseModel):
    metric_key: str
    window_days: int = 30


@router.post("/recompute")
def recompute(
    payload: BaselineRecomputeIn,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    # SECURITY: Override payload.user_id with authenticated user_id
    try:
        baseline = recompute_baseline(
            db=db,
            user_id=user_id,  # Use authenticated user_id, not payload.user_id
            metric_key=payload.metric_key,
            window_days=payload.window_days,
        )
        return {
            "user_id": baseline.user_id,
            "metric_key": baseline.metric_key,
            "mean": baseline.mean,
            "std": baseline.std,
            "updated_at": baseline.updated_at.isoformat(),
        }
    except BaselineUnavailable as e:
        # SECURITY FIX (Risk #5): Surface baseline errors explicitly
        status_code = 400 if not e.error.recoverable else 503
        raise HTTPException(
            status_code=status_code,
            detail={
                "error": e.error.error_type.value,
                "message": e.error.message,
                "recoverable": e.error.recoverable,
            },
        )

