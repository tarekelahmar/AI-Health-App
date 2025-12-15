from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index
from sqlalchemy.sql import func

from app.core.database import Base


class NotificationOutbox(Base):
    """
    Durable queue for notifications (Outbox pattern).

    We generate notifications inside the DB transaction, then a background job dispatches them.
    """

    __tablename__ = "notification_outbox"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    # channel: "inbox" (always), optional channels: "email", "push", "sms"
    channel = Column(String(32), nullable=False, default="inbox", index=True)

    # type is a stable semantic label used by downstream renderers (e.g. "daily_checkin_reminder")
    notification_type = Column(String(64), nullable=False, index=True)

    # dedupe_key prevents duplicates (e.g. "checkin_reminder:USERID:YYYY-MM-DD")
    dedupe_key = Column(String(128), nullable=True, index=True)

    # payload_json is a JSON string for simple portability (keep minimal, render later)
    payload_json = Column(Text, nullable=True)

    # delivery state
    is_dispatched = Column(Boolean, nullable=False, default=False, index=True)
    dispatched_at = Column(DateTime(timezone=True), nullable=True)

    # retry mechanics
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_outbox_user_channel_state", "user_id", "channel", "is_dispatched"),
        Index("ix_outbox_dedupe", "dedupe_key"),
    )

