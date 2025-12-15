from datetime import date

from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.api.schemas.checkins import DailyCheckInCreate, DailyCheckInUpdate, DailyCheckInResponse

from app.domain.repositories.daily_checkin_repository import DailyCheckInRepository
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/api/v1/checkins", tags=["checkins"])


@router.post("/upsert", response_model=DailyCheckInResponse)
def upsert_checkin(
    payload: DailyCheckInCreate,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db)
):
    # Override payload.user_id with authenticated user_id (prevent spoofing)
    payload.user_id = user_id
    repo = DailyCheckInRepository(db)
    obj = repo.upsert_for_date(
        user_id=payload.user_id,
        checkin_date=payload.checkin_date,
        sleep_quality=payload.sleep_quality,
        energy=payload.energy,
        mood=payload.mood,
        stress=payload.stress,
        notes=payload.notes,
        behaviors_json=payload.behaviors_json,
    )
    return obj


@router.patch("/{checkin_date}", response_model=DailyCheckInResponse)
def update_checkin(
    checkin_date: date,
    payload: DailyCheckInUpdate,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    repo = DailyCheckInRepository(db)
    obj = repo.upsert_for_date(
        user_id=user_id,
        checkin_date=checkin_date,
        sleep_quality=payload.sleep_quality,
        energy=payload.energy,
        mood=payload.mood,
        stress=payload.stress,
        notes=payload.notes,
        behaviors_json=payload.behaviors_json if payload.behaviors_json is not None else None,
        adherence_rate=payload.adherence_rate,
    )
    return obj


@router.get("/{checkin_date}", response_model=DailyCheckInResponse)
def get_checkin(
    checkin_date: date,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db)
):
    repo = DailyCheckInRepository(db)
    obj = repo.get_by_date(user_id=user_id, checkin_date=checkin_date)
    if not obj:
        # return an "empty" checkin shape via upsert with no fields
        obj = repo.upsert_for_date(user_id=user_id, checkin_date=checkin_date, behaviors_json={})
    return obj


@router.get("", response_model=list[DailyCheckInResponse])
def list_checkins(
    user_id: int = Depends(get_request_user_id),
    start_date: date = Query(...),
    end_date: date = Query(...),
    limit: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    repo = DailyCheckInRepository(db)
    return repo.list_range(user_id=user_id, start_date=start_date, end_date=end_date, limit=limit)
