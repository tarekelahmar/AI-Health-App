from fastapi import APIRouter, Query, HTTPException, Depends
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.domain.repositories.inbox_repository import InboxRepository
from app.api.schemas.inbox import InboxListOut, InboxItemOut, InboxMarkReadIn, InboxMarkAllReadIn
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/api/v1/inbox", tags=["inbox"])


def _to_out(item) -> InboxItemOut:
    return InboxItemOut(
        id=item.id,
        user_id=item.user_id,
        category=item.category,
        title=item.title,
        body=item.body,
        metadata=item.metadata_json,
        is_read=item.is_read,
        created_at=item.created_at.isoformat() if item.created_at else "",
    )


@router.get("", response_model=InboxListOut)
def list_inbox(
    user_id: int = Depends(get_request_user_id),
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    repo = InboxRepository(db)
    items = repo.list_by_user(user_id=user_id, limit=limit, unread_only=unread_only)
    return InboxListOut(count=len(items), items=[_to_out(i) for i in items])


@router.post("/mark-read", response_model=InboxItemOut)
def mark_read(payload: InboxMarkReadIn, user_id: int = Depends(get_request_user_id), db: Session = Depends(get_db)):
    # Override payload.user_id with authenticated user_id (prevent spoofing)
    payload.user_id = user_id
    repo = InboxRepository(db)
    item = repo.mark_read(user_id=payload.user_id, item_id=payload.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    return _to_out(item)


@router.post("/mark-all-read")
def mark_all_read(user_id: int = Depends(get_request_user_id), db: Session = Depends(get_db)):
    repo = InboxRepository(db)
    n = repo.mark_all_read(user_id=user_id)
    return {"ok": True, "updated": n}
