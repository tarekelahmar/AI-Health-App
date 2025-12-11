from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.wearable_service import WearableDataSynchronizer
from app.config.security import get_current_user
from app.domain.models.user import User

router = APIRouter()

@router.post("/sync")
def sync_wearables(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Trigger manual wearable data sync"""
    # Retrieve stored wearable tokens for user
    # sync_result = synchronizer.sync_user_data(current_user.id, tokens, db)
    return {"status": "syncing", "user_id": current_user.id}

@router.post("/connect/{wearable}")
def connect_wearable(wearable: str, code: str, current_user: User = Depends(get_current_user)):
    """OAuth callback for wearable connection"""
    if wearable == "fitbit":
        # Exchange auth code for access token
        # Store token securely in database
        pass
    return {"status": "connected", "wearable": wearable}
