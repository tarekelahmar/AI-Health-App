from fastapi import APIRouter, Query
from sqlalchemy.orm import Session
from typing import List
from fastapi import Depends

from app.api.schemas.insight import InsightResponse
from app.api.transformers.insight_transformer import transform_insight
from app.domain.repositories.insight_repository import InsightRepository
from app.engine.loop_runner import run_loop
from app.core.database import get_db

router = APIRouter(
    prefix="",
    tags=["insights"],
    dependencies=[]  # 🔥 HARD OVERRIDE — NO AUTH
)

@router.get(
    "/feed",
    response_model=dict,
    dependencies=[]  # 🔥 CRITICAL: overrides any global auth
)
def get_insight_feed(
    user_id: int = Query(...),
    limit: int = Query(50),
    db: Session = Depends(get_db)
):
    repo = InsightRepository(db)
    insights = repo.list_by_user(user_id=user_id, limit=limit)
    return {
        "count": len(insights),
        "items": [transform_insight(i) for i in insights],
    }

@router.post(
    "/run",
    response_model=dict,
    dependencies=[]  # 🔥 NO AUTH
)
def run_insights(
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    try:
        result = run_loop(db=db, user_id=user_id)
        return {
            "created": result["created"],
            "insights": [transform_insight(i) for i in result["items"]],
        }
    except Exception as e:
        # Return empty result on error instead of crashing
        return {
            "created": 0,
            "insights": [],
            "error": str(e) if str(e) else "Unknown error"
        }
