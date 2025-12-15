from __future__ import annotations
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.domain.models.inbox_item import InboxItem


class InboxRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, category: str, title: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> InboxItem:
        item = InboxItem(
            user_id=user_id,
            category=category,
            title=title,
            body=body,
            metadata_json=metadata or None,
            is_read=False,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_by_user(self, user_id: int, limit: int = 50, unread_only: bool = False) -> List[InboxItem]:
        q = self.db.query(InboxItem).filter(InboxItem.user_id == user_id)
        if unread_only:
            q = q.filter(InboxItem.is_read == False)  # noqa: E712
        return q.order_by(desc(InboxItem.created_at)).limit(limit).all()

    def mark_read(self, user_id: int, item_id: int) -> Optional[InboxItem]:
        item = self.db.query(InboxItem).filter(InboxItem.id == item_id, InboxItem.user_id == user_id).first()
        if not item:
            return None
        item.is_read = True
        self.db.commit()
        self.db.refresh(item)
        return item

    def mark_all_read(self, user_id: int) -> int:
        updated = (
            self.db.query(InboxItem)
            .filter(InboxItem.user_id == user_id, InboxItem.is_read == False)  # noqa: E712
            .update({"is_read": True})
        )
        self.db.commit()
        return int(updated or 0)

