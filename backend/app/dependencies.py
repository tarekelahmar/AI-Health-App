"""Shared dependencies for FastAPI routes"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.repositories import (
    UserRepository,
    LabResultRepository,
    WearableRepository,
    SymptomRepository,
    QuestionnaireRepository,
    InsightRepository,
    ProtocolRepository,
    HealthDataRepository,
)
from app.engine.reasoning.insight_generator import InsightEngine


def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    """Dependency to get UserRepository instance"""
    return UserRepository(db)


def get_lab_repo(db: Session = Depends(get_db)) -> LabResultRepository:
    """Dependency to get LabResultRepository instance"""
    return LabResultRepository(db)


def get_wearable_repo(db: Session = Depends(get_db)) -> WearableRepository:
    """Dependency to get WearableRepository instance"""
    return WearableRepository(db)


def get_symptom_repo(db: Session = Depends(get_db)) -> SymptomRepository:
    """Dependency to get SymptomRepository instance"""
    return SymptomRepository(db)


def get_questionnaire_repo(db: Session = Depends(get_db)) -> QuestionnaireRepository:
    """Dependency to get QuestionnaireRepository instance"""
    return QuestionnaireRepository(db)


def get_insight_repo(db: Session = Depends(get_db)) -> InsightRepository:
    """Dependency to get InsightRepository instance"""
    return InsightRepository(db)


def get_protocol_repo(db: Session = Depends(get_db)) -> ProtocolRepository:
    """Dependency to get ProtocolRepository instance"""
    return ProtocolRepository(db)


def get_health_data_repo(db: Session = Depends(get_db)) -> HealthDataRepository:
    """Dependency to get HealthDataRepository instance"""
    return HealthDataRepository(db)


def get_insight_engine(db: Session = Depends(get_db)) -> InsightEngine:
    """Dependency to get InsightEngine instance with all required repositories"""
    lab_repo = LabResultRepository(db)
    wearable_repo = WearableRepository(db)
    health_data_repo = HealthDataRepository(db)
    symptom_repo = SymptomRepository(db)
    insight_repo = InsightRepository(db)
    
    return InsightEngine(
        lab_repo=lab_repo,
        wearable_repo=wearable_repo,
        health_data_repo=health_data_repo,
        symptom_repo=symptom_repo,
        insight_repo=insight_repo,
    )
