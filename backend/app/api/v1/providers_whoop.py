from __future__ import annotations

import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.schemas.providers import (
    ProviderConnectResponse,
    ProviderCallbackResponse,
    ProviderSyncResponse,
    ProviderStatusResponse,
)
from app.domain.repositories.provider_token_repository import ProviderTokenRepository
from app.providers.whoop.whoop_adapter import WhoopAdapter
from app.providers.whoop.whoop_oauth import compute_expires_at
from app.engine.providers.provider_sync_service import ProviderSyncService

# Step Q dependency:
from app.api.auth_mode import get_request_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/providers/whoop", tags=["providers"])


@router.get("/status", response_model=ProviderStatusResponse)
def whoop_status(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    repo = ProviderTokenRepository(db)
    tok = repo.get(user_id=user_id, provider="whoop")
    return ProviderStatusResponse(provider="whoop", connected=bool(tok))


@router.get("/connect", response_model=ProviderConnectResponse)
def whoop_connect(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    # MVP: state stored client-side; in production store state in DB with TTL.
    adapter = WhoopAdapter(db)
    state = secrets.token_urlsafe(16)
    try:
        url = adapter.build_authorize_url(state=state)
    except RuntimeError as e:
        # Safety: Clear error message when credentials are missing
        logger.error(f"WHOOP connect failed for user_id={user_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"WHOOP connect failed for user_id={user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate WHOOP OAuth: {str(e)}")
    return ProviderConnectResponse(provider="whoop", authorize_url=url)


@router.get("/callback", response_model=ProviderCallbackResponse)
def whoop_callback(
    code: str = Query(...),
    state: Optional[str] = Query(None),
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    adapter = WhoopAdapter(db)
    repo = ProviderTokenRepository(db)

    try:
        token = adapter.exchange_code_for_token(code=code, redirect_uri=adapter.redirect_uri)
    except RuntimeError as e:
        # Safety: Clear error message when credentials are missing
        logger.error(f"WHOOP callback failed for user_id={user_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"WHOOP callback failed for user_id={user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {e}")

    access_token = token.get("access_token")
    if not access_token:
        logger.error(f"WHOOP callback: No access_token returned for user_id={user_id}")
        raise HTTPException(status_code=500, detail="No access_token returned from WHOOP")

    repo.upsert(
        user_id=user_id,
        provider="whoop",
        access_token=access_token,
        refresh_token=token.get("refresh_token"),
        token_type=token.get("token_type"),
        scope=token.get("scope"),
        expires_at=compute_expires_at(token.get("expires_in")),
    )
    logger.info(f"WHOOP connected successfully for user_id={user_id}")
    return ProviderCallbackResponse(provider="whoop", connected=True)


@router.post("/sync", response_model=ProviderSyncResponse)
def whoop_sync(
    user_id: int = Depends(get_request_user_id),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """
    Sync WHOOP data for a user.
    
    Safety: Never partially ingests data. All points are validated before insertion.
    """
    since = datetime.utcnow() - timedelta(days=days)
    svc = ProviderSyncService(db)
    try:
        res = svc.sync_whoop(user_id=user_id, since=since)
    except Exception as e:
        logger.error(f"WHOOP sync endpoint failed for user_id={user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
    return ProviderSyncResponse(**res)


# Import helper function
from app.providers.whoop.whoop_oauth import compute_expires_at

