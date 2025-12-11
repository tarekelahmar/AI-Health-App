from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.domain.models.user import User
from app.domain.models.insight import Insight
from app.core.database import get_db
from app.engine.reasoning.dysfunction_detector import DysfunctionDetector
from app.engine.rag.retriever import HealthRAGEngine
from app.config.settings import get_settings

router = APIRouter()

settings = get_settings()
detector = DysfunctionDetector(settings.HEALTH_ONTOLOGY_PATH)

# Lazy initialization of RAG engine to avoid import-time API key requirement
_rag_engine = None

def get_rag_engine():
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = HealthRAGEngine(settings.KNOWLEDGE_BASE_PATH)
    return _rag_engine

@router.post("/{user_id}")
def create_assessment(user_id: int, db: Session = Depends(get_db)):
    """Run comprehensive health assessment for user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Detect dysfunctions
    dysfunctions = detector.detect_dysfunctions(user_id, db, days=30)
    
    # Get RAG insights (lazy initialization)
    rag_engine = get_rag_engine()
    rag_insights = rag_engine.generate_health_insight({
        'age': 35,
        'symptoms': [],
        'labs': {},
        'wearables': {}
    })
    
    # Store assessments as insights
    assessment_ids = []
    for dysfunction in dysfunctions:
        insight = Insight(
            user_id=user_id,
            insight_type="dysfunction",
            title=dysfunction.get('name', dysfunction['dysfunction_id']),
            description=f"Detected {dysfunction['dysfunction_id']} with {dysfunction['severity']} severity",
            confidence_score=dysfunction.get('confidence', 0.5),
            metadata_json=str(dysfunction)
        )
        db.add(insight)
        db.flush()
        assessment_ids.append(insight.id)
    
    db.commit()
    
    return {
        "user_id": user_id,
        "assessment_ids": assessment_ids,
        "dysfunctions": dysfunctions,
        "rag_insights": rag_insights,
        "timestamp": datetime.utcnow()
    }

@router.get("/{user_id}")
def get_latest_assessment(user_id: int, db: Session = Depends(get_db)):
    """Get user's latest assessment"""
    insights = db.query(Insight).filter(
        Insight.user_id == user_id,
        Insight.insight_type == "dysfunction"
    ).order_by(Insight.generated_at.desc()).all()
    
    if not insights:
        raise HTTPException(status_code=404, detail="No assessments found")
    
    return insights
