"""Database connection and session management"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import logging

from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def init_db():
    """MVP-safe: create missing tables"""
    # Import all models to ensure they are registered with Base.metadata
    from app.domain.models.baseline import Baseline
    from app.domain.models.health_data_point import HealthDataPoint
    from app.domain.models.insight import Insight
    from app.domain.models.user import User
    from app.domain.models.lab_result import LabResult
    from app.domain.models.wearable_sample import WearableSample
    from app.domain.models.symptom import Symptom
    from app.domain.models.questionnaire import Questionnaire
    from app.domain.models.protocol import Protocol
    from app.domain.models.intervention import Intervention
    from app.domain.models.experiment import Experiment
    from app.domain.models.adherence_event import AdherenceEvent
    from app.domain.models.evaluation_result import EvaluationResult
    from app.domain.models.loop_decision import LoopDecision
    from app.domain.models.daily_checkin import DailyCheckIn
    from app.domain.models.causal_graph_edge import CausalGraphEdge
    from app.domain.models.causal_graph_snapshot import CausalGraphSnapshot
    from app.domain.models.intervention import Intervention
    from app.domain.models.protocol import Protocol
    from app.domain.models.inbox_item import InboxItem  # noqa: F401
    from app.domain.models.notification_outbox import NotificationOutbox  # noqa: F401
    from app.domain.models.insight_summary import InsightSummary  # noqa: F401
    from app.domain.models.narrative import Narrative  # noqa: F401
    from app.domain.models.provider_token import ProviderToken  # noqa: F401
    from app.domain.models.data_provenance import DataProvenance  # noqa: F401
    from app.domain.models.consent import Consent  # noqa: F401
    from app.domain.models.driver_finding import DriverFinding  # noqa: F401
    from app.domain.models.personal_driver import PersonalDriver  # noqa: F401
    from app.domain.models.decision_signal import DecisionSignal  # noqa: F401
    from app.domain.models.causal_memory import CausalMemory  # noqa: F401
    from app.domain.models.explanation_edge import ExplanationEdge  # noqa: F401
    from app.domain.models.trust_score import TrustScore  # noqa: F401
    from app.domain.models.personal_health_model import PersonalHealthModel  # noqa: F401
    from app.domain.models.audit_event import AuditEvent  # noqa: F401
    from app.domain.models.oauth_state import OAuthState  # noqa: F401
    from app.domain.models.job_run import JobRun  # noqa: F401 SECURITY FIX (Risk #10)
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    
    Yields:
        Database session
        
    Example:
        ```python
        def my_endpoint(db: Session = Depends(get_db)):
            # Use db session here
            pass
        ```
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

