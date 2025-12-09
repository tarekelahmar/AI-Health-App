"""Health assessment API endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.core.database import get_db, SessionLocal
from app import models
from app.services.dysfunction_detector import DysfunctionDetector
from app.services.rag_engine import HealthRAGEngine
from app.core.config import (
    HEALTH_ONTOLOGY_PATH,
    KNOWLEDGE_BASE_PATH,
    ASSESSMENT_DAYS
)

router = APIRouter(prefix="/assess", tags=["assessment"])

# Initialize services
detector = DysfunctionDetector(HEALTH_ONTOLOGY_PATH)
rag_engine = None  # Lazy initialization

def get_rag_engine():
    """Lazy initialization of RAG engine to avoid blocking server startup"""
    global rag_engine
    if rag_engine is None:
        print("Initializing RAG engine (this may take a moment)...")
        rag_engine = HealthRAGEngine(KNOWLEDGE_BASE_PATH)
        print("RAG engine initialized!")
    return rag_engine


@router.post("/{user_id}")
def assess_health(user_id: int, db: Session = Depends(get_db)):
    """
    Comprehensive health assessment for a user.
    Detects dysfunctions and generates RAG-backed insights.
    """
    
    # Get user
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Detect dysfunctions
    dysfunctions = detector.detect_dysfunctions(user_id, db, days=ASSESSMENT_DAYS)
    
    # Prepare user data for RAG
    recent_data = db.query(models.HealthDataPoint).filter(
        models.HealthDataPoint.user_id == user_id
    ).all()
    
    labs = {
        dp.data_type: dp.value 
        for dp in recent_data 
        if dp.source == 'lab'
    }
    wearables = {
        dp.data_type: dp.value 
        for dp in recent_data 
        if dp.source == 'wearable'
    }
    
    user_data = {
        'age': 35,  # In production, get from user profile
        'symptoms': ['fatigue'],  # In production, get from user input
        'labs': labs,
        'wearables': wearables
    }
    
    # Generate RAG-backed recommendations (lazy initialization)
    rag_response = get_rag_engine().generate_health_insight(user_data)
    
    # Save assessment
    for dysfunction in dysfunctions:
        assessment = models.HealthAssessment(
            user_id=user_id,
            dysfunction_id=dysfunction['dysfunction_id'],
            severity_level=dysfunction['severity'],
            notes=json.dumps({
                'confidence': dysfunction['confidence'],
                'evidence': dysfunction['evidence']
            })
        )
        db.add(assessment)
    
    db.commit()
    
    return {
        "user_id": user_id,
        "assessment_date": datetime.utcnow(),
        "detected_dysfunctions": dysfunctions,
        "rag_insights": rag_response['response'],
        "data_summary": {
            "labs": labs,
            "wearables": wearables
        }
    }

