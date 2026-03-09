"""
Actions API — endpoints for action detail screens.

Endpoints:
- GET /api/v1/actions/{action_id}/mentions  — journal messages mentioning the action
"""
from __future__ import annotations

from typing import List

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.domain.models.journal_message import JournalMessage

router = make_v1_router(prefix="/api/v1/actions", tags=["actions"])


# ── Response Schemas ─────────────────────────────────────────────

class ActionMentionResponse(BaseModel):
    date: str
    excerpt: str
    message_id: int


# ── Stop words for keyword extraction ────────────────────────────

STOP_WORDS = frozenset({
    'the', 'a', 'an', 'to', 'with', 'for', 'my', 'on', 'in', 'and', 'or',
    'of', 'it', 'is', 'be', 'at', 'by', 'this', 'that', 'have', 'has',
    'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
    'about', 'up', 'out', 'not', 'no', 'so', 'if', 'but', 'from', 'as',
    'i', 'me', 'we', 'you', 'he', 'she', 'they', 'them',
})


# ── Endpoints ────────────────────────────────────────────────────

@router.get(
    "/{action_id}/mentions",
    response_model=List[ActionMentionResponse],
    summary="Get journal messages that mention this action's topic",
)
def get_action_mentions(
    action_id: int,
    title: str = Query(..., description="Action title to search for keywords in journal messages"),
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
) -> List[ActionMentionResponse]:
    """
    Search the user's journal messages for content matching keywords
    extracted from the action title. Returns up to 10 matching messages
    in chronological order.

    Since we don't have an Action model yet, the title is passed as a
    query parameter so the frontend can supply it.
    """
    # Extract meaningful keywords from the title
    words = [
        w for w in title.lower().split()
        if w not in STOP_WORDS and len(w) > 2
    ]

    if not words:
        return []

    # Search user messages (role='user') for keyword matches
    # Use the first 3 keywords to avoid overly broad queries
    keyword_filters = [
        JournalMessage.content.ilike(f'%{w}%')
        for w in words[:3]
    ]

    messages = (
        db.query(JournalMessage)
        .filter(
            JournalMessage.user_id == user_id,
            JournalMessage.role == 'user',
            or_(*keyword_filters),
        )
        .order_by(JournalMessage.created_at.asc())
        .limit(10)
        .all()
    )

    return [
        ActionMentionResponse(
            date=m.created_at.strftime("%b %d"),
            excerpt=m.content[:120] + ("..." if len(m.content) > 120 else ""),
            message_id=m.id,
        )
        for m in messages
    ]
