"""
Journal V3 Chat API — streaming conversational companion.

Endpoints:
- POST /api/v1/journal/chat          — send message, stream SSE response
- POST /api/v1/journal/chat/score    — confirm daily score for a session
- GET  /api/v1/journal/sessions      — list recent sessions
- GET  /api/v1/journal/sessions/{id}/messages — get session transcript
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.engine.journal_chat_service import (
    resolve_session,
    save_message,
    stream_chat_response,
    confirm_daily_score,
    get_sessions_for_user,
    get_session_messages,
)

router = make_v1_router(prefix="/api/v1/journal", tags=["journal-chat"])


# ── Request/Response Schemas ──────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[int] = None


class ScoreConfirmRequest(BaseModel):
    session_id: int
    score: float = Field(..., ge=1.0, le=10.0)


class ScoreConfirmResponse(BaseModel):
    confirmed: bool
    score: float
    date: str


class SessionMessageInline(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class SessionSummary(BaseModel):
    id: int
    started_at: str
    daily_score: Optional[float] = None
    message_count: int
    preview: str
    summary: Optional[str] = None
    messages: Optional[List[SessionMessageInline]] = None


class SessionMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


# ── Endpoints ─────────────────────────────────────────────────────

@router.post("/chat", response_class=StreamingResponse)
async def chat(
    body: ChatRequest,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """
    Send a message and receive a streamed AI companion response via SSE.

    The response is a stream of Server-Sent Events:
    - data: {"type": "token", "content": "..."}   — streaming text chunks
    - data: {"type": "done", "session_id": N, "message_id": N}  — stream complete
    """
    # 1. Resolve or create session
    session = resolve_session(db, user_id, body.session_id)

    # 2. Save user message
    save_message(db, session.id, user_id, "user", body.message)
    db.commit()

    # 3. Stream response
    return StreamingResponse(
        stream_chat_response(db, user_id, session, body.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/score", response_model=ScoreConfirmResponse)
def confirm_score(
    body: ScoreConfirmRequest,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """
    Confirm the daily score for a session.

    This upserts a DailyCheckIn row for backward compatibility with
    the pattern engine, score history, synthesis, and milestones.
    """
    try:
        result = confirm_daily_score(db, user_id, body.session_id, body.score)
        return ScoreConfirmResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/sessions", response_model=List[SessionSummary])
def list_sessions(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=50, ge=1, le=200),
    include_messages: int = Query(default=0, ge=0, le=50,
                                  description="Include messages for the N most recent sessions"),
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """List recent journal sessions for the user."""
    return get_sessions_for_user(db, user_id, days=days, limit=limit,
                                 include_messages=include_messages)


@router.get("/sessions/{session_id}/messages", response_model=List[SessionMessageResponse])
def get_messages(
    session_id: int,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Get all messages for a session in chronological order."""
    messages = get_session_messages(db, user_id, session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found or empty")
    return messages
