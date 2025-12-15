from __future__ import annotations

import json
from datetime import date
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.domain.repositories.inbox_repository import InboxRepository
from app.domain.repositories.notification_outbox_repository import NotificationOutboxRepository


class NotificationService:
    """
    Single entry point for generating notifications.

    Writes:
      - InboxItem (UI-facing)
      - NotificationOutbox (dispatch-facing, optional additional channels)
    """

    def __init__(self, db: Session):
        self.db = db
        self.inbox = InboxRepository(db)
        self.outbox = NotificationOutboxRepository(db)

    def create_inbox_only(
        self,
        user_id: int,
        category: str,
        title: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
        dedupe_key: Optional[str] = None,
    ) -> None:
        # Optional dedupe through outbox, even if we only dispatch to inbox.
        # This makes "create" idempotent across scheduler runs.
        if dedupe_key:
            existing = self.outbox.exists_by_dedupe_key(dedupe_key)
            if existing:
                return

        self.inbox.create(
            user_id=user_id,
            category=category,
            title=title,
            body=body,
            metadata=metadata or {},
        )
        self.outbox.enqueue(
            user_id=user_id,
            channel="inbox",
            notification_type=category,
            payload_json=json.dumps({"title": title, "body": body, "metadata": metadata or {}}),
            dedupe_key=dedupe_key,
        )

    def daily_checkin_reminder(self, user_id: int, checkin_date: date) -> None:
        key = f"checkin_reminder:{user_id}:{checkin_date.isoformat()}"
        self.create_inbox_only(
            user_id=user_id,
            category="reminder",
            title="Daily check-in",
            body="Log sleep quality, energy, mood, stress, and any supplements/behaviours so we can track what works.",
            metadata={"checkin_date": checkin_date.isoformat()},
            dedupe_key=key,
        )

    def experiment_due_evaluation(self, user_id: int, experiment_id: int) -> None:
        key = f"experiment_due_eval:{user_id}:{experiment_id}"
        self.create_inbox_only(
            user_id=user_id,
            category="experiment",
            title="Experiment ready to evaluate",
            body="Your active experiment has enough data. Run an evaluation to see if it helped.",
            metadata={"experiment_id": experiment_id},
            dedupe_key=key,
        )

    def safety_warning(self, user_id: int, title: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        # Safety warnings should not be over-deduped; but still allow a key if you want.
        self.create_inbox_only(
            user_id=user_id,
            category="safety",
            title=title,
            body=body,
            metadata=metadata or {},
            dedupe_key=None,
        )

