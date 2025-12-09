"""Database connection and utilities"""
from app.core.database import engine, SessionLocal, Base, get_db
from app.models.database import User, HealthDataPoint, HealthAssessment


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


# Re-export for convenience
__all__ = ["engine", "SessionLocal", "Base", "get_db", "create_tables"]

