"""Protocol generation API endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app import models
from app.services.protocol_generator import ProtocolGenerator
from app.core.config import HEALTH_ONTOLOGY_PATH, ASSESSMENT_MAX_RESULTS

router = APIRouter(prefix="/protocol", tags=["protocol"])

# Initialize service
protocol_gen = ProtocolGenerator(HEALTH_ONTOLOGY_PATH)


@router.post("/{user_id}")
def generate_weekly_protocol(user_id: int, db: Session = Depends(get_db)):
    """Generate personalized weekly protocol based on latest assessment"""
    
    # Get latest assessments
    assessments = db.query(models.HealthAssessment).filter(
        models.HealthAssessment.user_id == user_id
    ).order_by(models.HealthAssessment.assessment_date.desc()).limit(ASSESSMENT_MAX_RESULTS).all()
    
    dysfunctions = [
        {
            'dysfunction_id': a.dysfunction_id,
            'severity': a.severity_level,
            'confidence': json.loads(a.notes).get('confidence', 0.5)
        }
        for a in assessments
    ]
    
    protocol = protocol_gen.generate_protocol(user_id, dysfunctions)
    
    return protocol

