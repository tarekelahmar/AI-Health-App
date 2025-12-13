"""Lab results endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.domain.models.lab_result import LabResult
from app.domain.schemas.lab_result import LabResultCreate, LabResultResponse
from app.core.database import get_db
from app.config.security import get_current_user
from app.domain.models.user import User
from app.services.observe import observe_signal
from app.api.public_router import public_router

router = public_router(prefix="", tags=["labs"])

@router.post("/", response_model=LabResultResponse, status_code=201)
def create_lab_result(
    lab_result: LabResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new lab result"""
    # Use observe_signal to validate, normalize, and score reliability
    signal = observe_signal(
        user_id=current_user.id,
        metric_key=lab_result.test_name,
        value=lab_result.value,
        unit=lab_result.unit,
        timestamp=datetime.utcnow(),  # LabResult model has default, but we use current time
        source="lab",
    )
    
    # Persist to LabResult using the validated/normalized signal
    db_lab = LabResult(
        user_id=signal.user_id,
        test_name=signal.metric_key,
        value=signal.value,
        unit=signal.unit,
        timestamp=signal.timestamp,
        reference_range=lab_result.reference_range,
        lab_name=lab_result.lab_name,
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

