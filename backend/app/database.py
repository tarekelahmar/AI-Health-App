"""Database connection and utilities"""
from app.core.database import engine, SessionLocal, Base, get_db
# Import all domain models to ensure they're registered with Base
from app.domain.models import (
    user, lab_result, wearable_sample, symptom, questionnaire, 
    insight, protocol, health_data_point
)


def create_tables():
    """
    Create all database tables.
    
    DEPRECATED: This function is kept for backward compatibility and testing.
    For production, use Alembic migrations instead:
        alembic upgrade head
    
    This function should NOT be used in production or for schema changes.
    All schema changes must go through Alembic migrations.
    """
    import warnings
    warnings.warn(
        "create_tables() is deprecated. Use 'alembic upgrade head' for migrations.",
        DeprecationWarning,
        stacklevel=2
    )
    Base.metadata.create_all(bind=engine)


# Re-export for convenience
__all__ = ["engine", "SessionLocal", "Base", "get_db", "create_tables"]

