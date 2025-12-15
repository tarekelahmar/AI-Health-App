from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.models.notification_outbox import NotificationOutbox
from app.api.schemas.outbox import OutboxItemResponse
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/api/v1/outbox", tags=["outbox"], public=False)


@router.get("", response_model=list[OutboxItemResponse])
def list_outbox(
    user_id: int = Depends(get_request_user_id),
    pending_only: bool = Query(False),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    # SECURITY: Use get_request_user_id which enforces auth in private mode
    
    q = db.query(NotificationOutbox).filter(NotificationOutbox.user_id == user_id)
    if pending_only:
        q = q.filter(NotificationOutbox.is_dispatched == False)  # noqa: E712
    return q.order_by(NotificationOutbox.created_at.desc()).limit(limit).all()
