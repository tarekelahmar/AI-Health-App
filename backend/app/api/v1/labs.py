"""Lab results endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.domain.models.lab_result import LabResult
from app.domain.schemas.lab_result import LabResultCreate, LabResultResponse
from app.core.database import get_db
from app.config.security import get_current_user
from app.domain.models.user import User

router = APIRouter()

@router.post("/", response_model=LabResultResponse, status_code=201)
def create_lab_result(
    lab_result: LabResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new lab result"""
    db_lab = LabResult(
        user_id=current_user.id,
        **lab_result.model_dump()
    )
    db.add(db_lab)
    db.commit()
    db.refresh(db_lab)
    return db_lab

@router.get("/", response_model=List[LabResultResponse])
def list_lab_results(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all lab results for current user"""
    return db.query(LabResult).filter(LabResult.user_id == current_user.id).all()

