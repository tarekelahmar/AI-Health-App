"""Database connection and utilities"""
from app.core.database import engine, SessionLocal, Base, get_db
# Import all domain models to ensure they're registered with Base
from app.domain.models import (
    user, lab_result, wearable_sample, symptom, questionnaire, 
    insight, protocol, health_data_point
)


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


# Re-export for convenience
__all__ = ["engine", "SessionLocal", "Base", "get_db", "create_tables"]

