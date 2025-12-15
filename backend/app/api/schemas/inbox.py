from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class InboxItemOut(BaseModel):
    id: int
    user_id: int
    category: str
    title: str
    body: str
    metadata: Optional[Dict[str, Any]] = None
    is_read: bool
    created_at: str


class InboxListOut(BaseModel):
    count: int
    items: List[InboxItemOut]


class InboxMarkReadIn(BaseModel):
    user_id: int
    item_id: int


class InboxMarkAllReadIn(BaseModel):
    user_id: int

