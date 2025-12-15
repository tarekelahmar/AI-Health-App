from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.domain.models.notification_outbox import NotificationOutbox


class NotificationOutboxRepository:
    def __init__(self, db: Session):
        self.db = db

    def exists_by_dedupe_key(self, dedupe_key: str) -> bool:
        return (
            self.db.query(NotificationOutbox)
            .filter(NotificationOutbox.dedupe_key == dedupe_key)
            .first()
            is not None
        )

    def enqueue(
        self,
        user_id: int,
        channel: str,
        notification_type: str,
        payload_json: Optional[str] = None,
        dedupe_key: Optional[str] = None,
    ) -> NotificationOutbox:
        if dedupe_key and self.exists_by_dedupe_key(dedupe_key):
            # Dedupe: return existing row to keep behavior idempotent
            return (
                self.db.query(NotificationOutbox)
                .filter(NotificationOutbox.dedupe_key == dedupe_key)
                .first()
            )

        row = NotificationOutbox(
            user_id=user_id,
            channel=channel,
            notification_type=notification_type,
            payload_json=payload_json,
            dedupe_key=dedupe_key,
            is_dispatched=False,
            attempt_count=0,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def list_pending(self, limit: int = 100) -> List[NotificationOutbox]:
        return (
            self.db.query(NotificationOutbox)
            .filter(NotificationOutbox.is_dispatched == False)  # noqa: E712
            .order_by(NotificationOutbox.created_at.asc())
            .limit(limit)
            .all()
        )

    def mark_dispatched(self, outbox_id: int) -> None:
        row = self.db.query(NotificationOutbox).get(outbox_id)
        if not row:
            return
        row.is_dispatched = True
        row.dispatched_at = datetime.utcnow()
        self.db.add(row)

    def mark_failed(self, outbox_id: int, error: str) -> None:
        row = self.db.query(NotificationOutbox).get(outbox_id)
        if not row:
            return
        row.attempt_count = (row.attempt_count or 0) + 1
        row.last_error = error[:4000]
        self.db.add(row)

