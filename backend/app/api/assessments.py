from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database import User, HealthAssessment
from app.database import get_db
from app.services.dysfunction_detector import DysfunctionDetector
from app.services.rag_engine import HealthRAGEngine
from app.config import get_settings

router = APIRouter()

settings = get_settings()
detector = DysfunctionDetector(settings.HEALTH_ONTOLOGY_PATH)
rag_engine = HealthRAGEngine(settings.KNOWLEDGE_BASE_PATH)

@router.post("/{user_id}")
def create_assessment(user_id: int, db: Session = Depends(get_db)):
    """Run comprehensive health assessment for user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Detect dysfunctions
    dysfunctions = detector.detect_dysfunctions(user_id, db, days=30)
    
    # Get RAG insights
    rag_insights = rag_engine.generate_health_insight({
        'age': 35,
        'symptoms': [],
        'labs': {},
        'wearables': {}
    })
    
    # Store assessments
    assessment_ids = []
    for dysfunction in dysfunctions:
        assessment = HealthAssessment(
            user_id=user_id,
            dysfunction_id=dysfunction['dysfunction_id'],
            severity_level=dysfunction['severity'],
            notes=f"Confidence: {dysfunction['confidence']}"
        )
        db.add(assessment)
        db.flush()
        assessment_ids.append(assessment.id)
    
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
    assessments = db.query(HealthAssessment).filter(
        HealthAssessment.user_id == user_id
    ).order_by(HealthAssessment.assessment_date.desc()).first()
    
    if not assessments:
        raise HTTPException(status_code=404, detail="No assessments found")
    
    return assessments
