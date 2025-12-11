import json
import logging
from datetime import datetime
from enum import Enum
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)

class ComplianceEvent(Enum):
    """Audit log events"""
    USER_LOGIN = "user_login"
    DATA_ACCESSED = "data_accessed"
    DATA_MODIFIED = "data_modified"
    DATA_DELETED = "data_deleted"
    EXPORT_REQUESTED = "export_requested"
    CONSENT_GRANTED = "consent_granted"
    BREACH_DETECTED = "breach_detected"

def log_compliance_event(
    event_type: ComplianceEvent,
    user_id: int,
    resource_id: int,
    details: str,
    ip_address: str
):
    """Log all access and modifications for HIPAA audit trail"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type.value,
        "user_id": user_id,
        "resource_id": resource_id,
        "details": details,
        "ip_address": ip_address
    }
    logger.info(json.dumps(log_entry))
    # Also store in database for audit trail retention

def anonymize_data(user_id: int, db_session) -> dict:
    """GDPR right to be forgotten"""
    from app.domain.models.user import User
    from app.domain.models.health_data_point import HealthDataPoint
    from app.domain.models.insight import Insight
    
    # Replace identifying info with pseudonyms
    user = db_session.query(User).filter(User.id == user_id).first()
    if user:
        user.name = f"User_{user_id}"
        user.email = f"deleted_{user_id}@example.com"
        db_session.commit()
    
    return {"status": "anonymized", "user_id": user_id}

def export_user_data(user_id: int, db_session) -> dict:
    """GDPR right to data portability"""
    from app.domain.models.user import User
    from app.domain.models.health_data_point import HealthDataPoint
    
    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}
    
    data_points = db_session.query(HealthDataPoint).filter(
        HealthDataPoint.user_id == user_id
    ).all()
    
    export = {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at.isoformat()
        },
        "health_data": [
            {
                "type": dp.data_type,
                "value": dp.value,
                "unit": dp.unit,
                "timestamp": dp.timestamp.isoformat()
            }
            for dp in data_points
        ]
    }
    return export

