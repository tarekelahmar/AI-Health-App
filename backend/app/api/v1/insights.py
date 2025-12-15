from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from typing import List

from app.api.schemas.insight import InsightResponse
from app.api.transformers.insight_transformer import transform_insight
from app.domain.repositories.insight_repository import InsightRepository
from app.engine.loop_runner import run_loop
from app.core.database import get_db
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/api/v1/insights", tags=["insights"])

@router.get("/feed", response_model=dict)
def get_insight_feed(
    user_id: int = Depends(get_request_user_id),
    limit: int = Query(50),
    db: Session = Depends(get_db)
):
    repo = InsightRepository(db)
    insights = repo.list_by_user(user_id=user_id, limit=limit)
    return {
        "count": len(insights),
        "items": [transform_insight(i) for i in insights],
    }

@router.post("/run", response_model=dict)
def run_insights(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db)
):
    """
    Run insight generation loop for user.
    
    WEEK 4: Explicit error handling - no silent failures.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        result = run_loop(db=db, user_id=user_id)
        return {
            "created": result["created"],
            "insights": [transform_insight(i) for i in result["items"]],
        }
    except Exception as e:
        # WEEK 4: Log error with structured logging, return explicit error response
        logger.error(
            "insight_generation_failed",
            extra={
                "user_id": user_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        # Return explicit error - don't silently return empty success
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Insight generation failed: {str(e)}. Check logs for details."
        )
