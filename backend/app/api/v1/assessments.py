from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.domain.models.user import User
from app.domain.models.insight import Insight
from app.core.database import get_db
from app.engine.reasoning.dysfunction_detector import DysfunctionDetector
from app.engine.rag.retriever import HealthRAGEngine
from app.config.settings import get_settings
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.config.environment import get_mode_config, is_production, is_staging

# SECURITY FIX (Week 1): Use make_v1_router to enforce auth
router = make_v1_router(prefix="/api/v1/assessments", tags=["assessments"])

settings = get_settings()
config = get_mode_config()

# WEEK 3: Only initialize if enabled (disabled in staging/production)
detector = None
if config.get("enable_dysfunction_detection", False):
    detector = DysfunctionDetector(settings.HEALTH_ONTOLOGY_PATH)

# Lazy initialization of RAG engine to avoid import-time API key requirement
_rag_engine = None

def get_rag_engine():
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = HealthRAGEngine(settings.KNOWLEDGE_BASE_PATH)
    return _rag_engine

@router.post("")
def create_assessment(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db)
):
    """
    Run comprehensive health assessment for user.
    
    SECURITY FIX (Week 1): user_id now comes from authenticated request, not path parameter.
    WEEK 3: Prescriptive/diagnostic features disabled in staging/production.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # WEEK 3: Check if prescriptive features are enabled
    if is_production() or is_staging():
        raise HTTPException(
            status_code=403,
            detail="Assessment endpoint disabled in staging/production. "
                   "This endpoint uses prescriptive/diagnostic features that violate system boundaries."
        )
    
    if not config.get("enable_dysfunction_detection", False):
        raise HTTPException(
            status_code=403,
            detail="Dysfunction detection is disabled. Set ENABLE_DYSFUNCTION_DETECTION=true to enable (dev only)."
        )
    
    if not detector:
        raise HTTPException(
            status_code=503,
            detail="Dysfunction detector not initialized"
        )
    
    # Detect dysfunctions (only if enabled)
    dysfunctions = detector.detect_dysfunctions(user_id, db, days=30)
    
    # WEEK 3: RAG is disabled in staging/production
    rag_insights = None
    if config.get("enable_rag", False):
        rag_engine = get_rag_engine()
        rag_insights = rag_engine.generate_health_insight({
            'age': 35,
            'symptoms': [],
            'labs': {},
            'wearables': {}
        })
    else:
        rag_insights = {"note": "RAG engine disabled - prescriptive features not available"}
    
    # WEEK 3: Don't store "dysfunction" insights - this is diagnostic framing
    # Instead, return as assessment data only (not persisted as insights)
    assessment_ids = []
    # Removed: storing dysfunction insights violates non-diagnostic boundary
    
    db.commit()
    
    return {
        "user_id": user_id,
        "assessment_ids": assessment_ids,
        "dysfunctions": dysfunctions,  # Returned but not persisted
        "rag_insights": rag_insights,
        "timestamp": datetime.utcnow(),
        "warning": "Assessment data returned for review only. Not stored as insights due to diagnostic framing."
    }

@router.get("")
def get_latest_assessment(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db)
):
    """
    Get user's latest assessment.
    
    SECURITY FIX (Week 1): user_id now comes from authenticated request, not path parameter.
    WEEK 3: This endpoint is deprecated - dysfunction insights are no longer stored.
    """
    # WEEK 3: Dysfunction insights are no longer stored (diagnostic framing violation)
    # Return empty or redirect to regular insights
    return {
        "message": "Assessment endpoint deprecated. Dysfunction insights are no longer stored due to diagnostic framing concerns.",
        "suggested_endpoint": "/api/v1/insights/feed",
        "insights": []
    }
