"""User preferences API — depth level, onboarding status."""

from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.core.database import get_db
from app.domain.models.user_preference import UserPreference

router = make_v1_router(prefix="/api/v1/preferences", tags=["preferences"])


class PreferenceResponse(BaseModel):
    preferred_depth_level: int
    journal_onboarded: bool

    class Config:
        from_attributes = True


class PreferenceUpdate(BaseModel):
    preferred_depth_level: int = Field(None, ge=1, le=3)
    journal_onboarded: bool = None


def _get_or_create(db: Session, user_id: int) -> UserPreference:
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not pref:
        from datetime import datetime
        pref = UserPreference(user_id=user_id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


@router.get("", response_model=PreferenceResponse)
def get_preferences(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    return _get_or_create(db, user_id)


@router.patch("", response_model=PreferenceResponse)
def update_preferences(
    payload: PreferenceUpdate,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    pref = _get_or_create(db, user_id)
    if payload.preferred_depth_level is not None:
        pref.preferred_depth_level = payload.preferred_depth_level
    if payload.journal_onboarded is not None:
        pref.journal_onboarded = payload.journal_onboarded
    db.commit()
    db.refresh(pref)
    return pref
