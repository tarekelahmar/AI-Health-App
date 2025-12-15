from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.models.notification_outbox import NotificationOutbox
from app.api.schemas.outbox import OutboxItemResponse
from app.api.auth_mode import get_current_user_optional, is_private_mode
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/api/v1/outbox", tags=["outbox"], public=False)


@router.get("", response_model=list[OutboxItemResponse])
def list_outbox(
    current_user=Depends(get_current_user_optional),
    user_id: int = Query(None),
    pending_only: bool = Query(False),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    if not is_private_mode():
        raise HTTPException(status_code=403, detail="Outbox debug endpoint disabled in AUTH_MODE=public")
    
    # In private mode, use current_user.id; in public mode this would have failed above
    effective_user_id = current_user.id if current_user else user_id
    if effective_user_id is None:
        raise HTTPException(status_code=400, detail="user_id required")
    
    q = db.query(NotificationOutbox).filter(NotificationOutbox.user_id == effective_user_id)
    if pending_only:
        q = q.filter(NotificationOutbox.is_dispatched == False)  # noqa: E712
    return q.order_by(NotificationOutbox.created_at.desc()).limit(limit).all()
