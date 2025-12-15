from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class OutboxItemResponse(BaseModel):
    id: int
    user_id: int
    channel: str
    notification_type: str
    dedupe_key: Optional[str] = None
    is_dispatched: bool
    dispatched_at: Optional[datetime] = None
    attempt_count: int
    last_error: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

