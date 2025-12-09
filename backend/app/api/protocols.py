from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import User, HealthAssessment
from app.database import get_db
from app.services.protocol_generator import ProtocolGenerator
from app.config import get_settings

router = APIRouter()

settings = get_settings()
protocol_gen = ProtocolGenerator(settings.HEALTH_ONTOLOGY_PATH)

@router.post("/{user_id}")
def generate_protocol(user_id: int, db: Session = Depends(get_db)):
    """Generate weekly protocol based on latest assessment"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get latest assessments
    assessments = db.query(HealthAssessment).filter(
        HealthAssessment.user_id == user_id
    ).order_by(HealthAssessment.assessment_date.desc()).limit(5).all()
    
    if not assessments:
        raise HTTPException(status_code=400, detail="No assessments found. Run assessment first.")
    
    dysfunctions = [
        {
            'dysfunction_id': a.dysfunction_id,
            'severity': a.severity_level,
            'confidence': 0.7
        }
        for a in assessments
    ]
    
    protocol = protocol_gen.generate_protocol(user_id, dysfunctions)
    return protocol
