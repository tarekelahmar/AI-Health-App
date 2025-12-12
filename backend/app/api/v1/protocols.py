from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.domain.models.user import User
from app.domain.models.insight import Insight
from app.domain.models.protocol import Protocol
from app.core.database import get_db
from app.engine.reasoning.protocol_generator import ProtocolGenerator
from app.config.settings import get_settings
from app.config.rate_limiting import rate_limit_user

router = APIRouter()

settings = get_settings()
protocol_gen = ProtocolGenerator(settings.HEALTH_ONTOLOGY_PATH)

@router.post("/{user_id}")
@rate_limit_user(settings.RATE_LIMIT_LLM if settings.ENABLE_RATE_LIMITING else "1000/minute")
def generate_protocol(user_id: int, db: Session = Depends(get_db)):
    """Generate weekly protocol based on latest assessment"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get latest insights (assessments)
    insights = db.query(Insight).filter(
        Insight.user_id == user_id,
        Insight.insight_type == "dysfunction"
    ).order_by(Insight.generated_at.desc()).limit(5).all()
    
    if not insights:
        raise HTTPException(status_code=400, detail="No assessments found. Run assessment first.")
    
    # Parse dysfunctions from insights
    dysfunctions = []
    for insight in insights:
        # Extract dysfunction info from metadata or title
        dysfunctions.append({
            'dysfunction_id': insight.title.lower().replace(' ', '_'),
            'severity': 'moderate',  # Would parse from metadata
            'confidence': insight.confidence_score
        })
    
    protocol = protocol_gen.generate_protocol(user_id, dysfunctions)
    return protocol
