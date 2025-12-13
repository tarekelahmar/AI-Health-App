from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.engine.baseline_service import recompute_baseline

router = APIRouter(prefix="/baselines", tags=["baselines"])


class BaselineRecomputeIn(BaseModel):
    user_id: int
    metric_key: str
    window_days: int = 30


@router.post("/recompute")
def recompute(payload: BaselineRecomputeIn, db: Session = Depends(get_db)):
    baseline = recompute_baseline(
        db=db,
        user_id=payload.user_id,
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

