"""Symptoms endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.domain.models.symptom import Symptom
from app.domain.schemas.symptom import SymptomCreate, SymptomResponse
from app.core.database import get_db
from app.config.security import get_current_user
from app.domain.models.user import User

router = APIRouter()

@router.post("/", response_model=SymptomResponse, status_code=201)
def create_symptom(
    symptom: SymptomCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new symptom entry"""
    db_symptom = Symptom(
        user_id=current_user.id,
        **symptom.model_dump()
    )
    db.add(db_symptom)
    db.commit()
    db.refresh(db_symptom)
    return db_symptom

@router.get("/", response_model=List[SymptomResponse])
def list_symptoms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all symptoms for current user"""
    return db.query(Symptom).filter(Symptom.user_id == current_user.id).all()

