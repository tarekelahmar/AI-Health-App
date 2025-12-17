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
    
    SCHEMA GOVERNANCE: Only works in dev mode.
    In staging/production, schema must be managed via Alembic migrations only.
    """
    from app.config.environment import is_production, is_staging
    import logging
    
    logger = logging.getLogger(__name__)
    
    # SCHEMA GOVERNANCE: Disable create_all() in staging/production
    if is_production() or is_staging():
        logger.warning(
            "create_tables() called in %s mode - create_all() is disabled. "
            "Schema must be managed via Alembic migrations only.",
            "production" if is_production() else "staging"
        )
        return
    
    # Only in dev mode: create missing tables (for convenience)
    import warnings
    warnings.warn(
        "create_tables() is deprecated. Use 'alembic upgrade head' for migrations.",
        DeprecationWarning,
        stacklevel=2
    )
    Base.metadata.create_all(bind=engine)


# Re-export for convenience
__all__ = ["engine", "SessionLocal", "Base", "get_db", "create_tables"]

