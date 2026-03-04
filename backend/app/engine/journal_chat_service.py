"""
Journal V3 Chat Service — streaming conversational companion.

Architecture (Option A — as specified):
1. Stream the conversational response via SSE (fast, natural text)
2. After stream completes, run a separate non-streamed analysis call
   (dimensions, context tags, factors) and store silently

When LLM is disabled, returns a deterministic placeholder response.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, date
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.domain.models.journal_session import JournalSession
from app.domain.models.journal_message import JournalMessage
from app.domain.models.daily_checkin import DailyCheckIn
from app.engine.prompts.journal_chat_system import build_chat_system_prompt
from app.engine.prompts.journal_analysis_system import build_analysis_prompt

logger = logging.getLogger(__name__)

# Session gap threshold: >4 hours since last message = new session
SESSION_GAP_HOURS = 4


# ── Session Management ─────────────────────────────────────────────

def resolve_session(db: Session, user_id: int, session_id: Optional[int] = None) -> JournalSession:
    """
    Find or create a session for the current message.

    Rules:
    - If session_id given and valid, use it
    - Otherwise, find the most recent session for this user
    - Create new session if:
        - No session exists for today, OR
        - Last message in the most recent session was >4 hours ago
    """
    now = datetime.utcnow()

    # If explicit session_id, validate and return
    if session_id is not None:
        session = db.query(JournalSession).filter(
            JournalSession.id == session_id,
            JournalSession.user_id == user_id,
        ).first()
        if session:
            return session

    # Find most recent session for this user
    latest = (
        db.query(JournalSession)
        .filter(JournalSession.user_id == user_id)
        .order_by(JournalSession.started_at.desc())
        .first()
    )

    if latest:
        # Check if the session is "alive" — last message < 4 hours ago
        last_message = (
            db.query(JournalMessage)
            .filter(JournalMessage.session_id == latest.id)
            .order_by(JournalMessage.created_at.desc())
            .first()
        )

        if last_message:
            gap = now - last_message.created_at
            if gap < timedelta(hours=SESSION_GAP_HOURS):
                return latest
        else:
            # Session exists but no messages yet (edge case) — use it if recent
            gap = now - latest.started_at
            if gap < timedelta(hours=SESSION_GAP_HOURS):
                return latest

    # Create new session
    new_session = JournalSession(
        user_id=user_id,
        started_at=now,
        created_at=now,
    )
    db.add(new_session)
    db.flush()  # Get the ID
    return new_session


def save_message(
    db: Session,
    session_id: int,
    user_id: int,
    role: str,
    content: str,
    ai_analysis_json: Optional[Dict] = None,
) -> JournalMessage:
    """Save a message to the database."""
    msg = JournalMessage(
        session_id=session_id,
        user_id=user_id,
        role=role,
        content=content,
        ai_analysis_json=ai_analysis_json,
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    db.flush()
    return msg


# ── Context Assembly ──────────────────────────────────────────────

def _build_conversation_messages(db: Session, session: JournalSession) -> List[Dict[str, str]]:
    """Build Anthropic-format message list from session transcript."""
    messages = (
        db.query(JournalMessage)
        .filter(JournalMessage.session_id == session.id)
        .order_by(JournalMessage.created_at.asc())
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in messages]


def _build_previous_session_text(db: Session, user_id: int, current_session_id: int) -> str:
    """Build text summary of the previous session for context."""
    prev_session = (
        db.query(JournalSession)
        .filter(
            JournalSession.user_id == user_id,
            JournalSession.id != current_session_id,
        )
        .order_by(JournalSession.started_at.desc())
        .first()
    )

    if not prev_session:
        return "No previous session."

    # If it has a summary, use that
    if prev_session.summary:
        score_note = f" (score: {prev_session.daily_score})" if prev_session.daily_score else ""
        return f"PREVIOUS SESSION ({prev_session.started_at.date()}{score_note}):\n{prev_session.summary}"

    # Otherwise, include full transcript (capped)
    messages = (
        db.query(JournalMessage)
        .filter(JournalMessage.session_id == prev_session.id)
        .order_by(JournalMessage.created_at.asc())
        .limit(20)
        .all()
    )

    if not messages:
        return "No previous session."

    lines = [f"PREVIOUS SESSION ({prev_session.started_at.date()}):"]
    for m in messages:
        prefix = "User" if m.role == "user" else "Companion"
        # Truncate long messages
        content = m.content[:300]
        if len(m.content) > 300:
            content += "..."
        lines.append(f"  {prefix}: {content}")

    if prev_session.daily_score:
        lines.append(f"  Score: {prev_session.daily_score}")

    return "\n".join(lines)


def _get_context_from_companion(db: Session, user_id: int) -> Tuple[str, str]:
    """
    Reuse context building from the V2 companion module.
    Returns (rolling_summary_text, active_patterns_text).
    """
    try:
        from app.engine.journal_companion import (
            _format_rolling_summary,
            _format_active_patterns,
        )
        rolling = _format_rolling_summary(db, user_id)
        patterns = _format_active_patterns(db, user_id)
        return rolling, patterns
    except Exception as e:
        logger.warning(f"Could not build companion context: {e}")
        return "Summary unavailable.", "No confirmed patterns yet."


# ── Streaming Response ────────────────────────────────────────────

async def stream_chat_response(
    db: Session,
    user_id: int,
    session: JournalSession,
    user_message_text: str,
) -> AsyncGenerator[str, None]:
    """
    Stream the companion's conversational response via SSE.

    Yields SSE-formatted lines:
    - data: {"type": "token", "content": "..."}
    - data: {"type": "done", "session_id": N, "message_id": N}

    After streaming, runs the analysis call silently and stores results.
    """
    enable_llm = os.getenv("ENABLE_LLM_TRANSLATION", "false").lower() == "true"

    if not enable_llm:
        # Deterministic fallback — simple ack
        fallback_text = "Check-in noted. LLM companion is currently disabled."
        assistant_msg = save_message(db, session.id, user_id, "assistant", fallback_text)
        db.commit()
        yield f"data: {json.dumps({'type': 'token', 'content': fallback_text})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'session_id': session.id, 'message_id': assistant_msg.id})}\n\n"
        return

    # ── Build context ──
    rolling_summary, active_patterns = _get_context_from_companion(db, user_id)
    previous_session_text = _build_previous_session_text(db, user_id, session.id)

    system_prompt = build_chat_system_prompt(
        active_patterns_text=active_patterns,
        rolling_summary_text=rolling_summary,
        previous_session_text=previous_session_text,
    )

    # Build conversation history (including the new user message, already saved)
    conversation_messages = _build_conversation_messages(db, session)

    # ── Stream from Anthropic ──
    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed")
        fallback_text = "Companion unavailable (anthropic package not installed)."
        assistant_msg = save_message(db, session.id, user_id, "assistant", fallback_text)
        db.commit()
        yield f"data: {json.dumps({'type': 'token', 'content': fallback_text})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'session_id': session.id, 'message_id': assistant_msg.id})}\n\n"
        return

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set")
        fallback_text = "Companion unavailable (API key not configured)."
        assistant_msg = save_message(db, session.id, user_id, "assistant", fallback_text)
        db.commit()
        yield f"data: {json.dumps({'type': 'token', 'content': fallback_text})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'session_id': session.id, 'message_id': assistant_msg.id})}\n\n"
        return

    model = os.getenv(
        "ANTHROPIC_COMPANION_MODEL",
        os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250514"),
    )

    full_response = ""

    try:
        client = anthropic.Anthropic(api_key=api_key)

        with client.messages.stream(
            model=model,
            max_tokens=800,
            system=system_prompt,
            messages=conversation_messages,
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                yield f"data: {json.dumps({'type': 'token', 'content': text})}\n\n"

    except Exception as e:
        logger.error(f"Streaming failed: {e}")
        if not full_response:
            full_response = "I'm having trouble responding right now. Your message has been saved."
            yield f"data: {json.dumps({'type': 'token', 'content': full_response})}\n\n"

    # ── Governance validation ──
    from app.engine.journal_companion import _validate_companion_text, FORBIDDEN_PHRASES
    validated = _validate_companion_text(full_response)
    if validated is None:
        full_response = "I generated a response that didn't meet safety guidelines. Your message has been saved."
        # Note: user already saw the streamed tokens. In production, consider more
        # sophisticated governance (e.g., token-level filtering). For now, we save
        # the sanitized version.

    # ── Save assistant message ──
    assistant_msg = save_message(db, session.id, user_id, "assistant", full_response)
    db.commit()

    yield f"data: {json.dumps({'type': 'done', 'session_id': session.id, 'message_id': assistant_msg.id})}\n\n"

    # ── Run analysis silently (non-streamed second call) ──
    try:
        analysis = _run_analysis(client, model, conversation_messages, user_id)
        if analysis:
            assistant_msg.ai_analysis_json = analysis
            db.commit()
    except Exception as e:
        logger.error(f"Analysis extraction failed (non-fatal): {e}")


def _run_analysis(
    client: Any,
    model: str,
    conversation_messages: List[Dict[str, str]],
    user_id: int,
) -> Optional[Dict]:
    """
    Second LLM call: extract structured analysis from the conversation.
    This is non-streamed and runs after the conversational response.
    """
    try:
        from app.llm.factor_extraction import FACTOR_KEYS
        factor_keys_text = ", ".join(FACTOR_KEYS)
    except ImportError:
        factor_keys_text = ""

    analysis_prompt = build_analysis_prompt(factor_keys_text=factor_keys_text)

    # Build a condensed transcript for the analysis call
    transcript_lines = []
    for msg in conversation_messages:
        role_label = "User" if msg["role"] == "user" else "Companion"
        transcript_lines.append(f"{role_label}: {msg['content']}")
    transcript = "\n".join(transcript_lines)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            system=analysis_prompt,
            messages=[{
                "role": "user",
                "content": f"Analyse this conversation transcript:\n\n{transcript}",
            }],
        )

        content = response.content[0].text if response.content else None
        if not content:
            return None

        # Strip markdown fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()

        return json.loads(content)

    except json.JSONDecodeError as e:
        logger.error(f"Analysis: invalid JSON from LLM: {e}")
        return None
    except Exception as e:
        logger.error(f"Analysis LLM call failed: {e}")
        return None


# ── Score Confirmation ─────────────────────────────────────────────

def confirm_daily_score(
    db: Session,
    user_id: int,
    session_id: int,
    score: float,
) -> Dict[str, Any]:
    """
    Confirm the daily score for a session.

    1. Update session.daily_score and score_confirmed_at
    2. Upsert DailyCheckIn for backward compatibility
    3. Run domain scoring
    4. Trigger milestone detection

    Returns: {"confirmed": True, "score": float, "date": str}
    """
    now = datetime.utcnow()

    # 1. Update session
    session = db.query(JournalSession).filter(
        JournalSession.id == session_id,
        JournalSession.user_id == user_id,
    ).first()

    if not session:
        raise ValueError(f"Session {session_id} not found for user {user_id}")

    session.daily_score = score
    session.score_confirmed_at = now

    # 2. Build notes from all user messages in this session
    user_messages = (
        db.query(JournalMessage)
        .filter(
            JournalMessage.session_id == session_id,
            JournalMessage.role == "user",
        )
        .order_by(JournalMessage.created_at.asc())
        .all()
    )
    combined_notes = "\n\n".join(m.content for m in user_messages)
    word_count = sum(len(m.content.split()) for m in user_messages)

    # Get analysis from the latest assistant message (if available)
    latest_assistant = (
        db.query(JournalMessage)
        .filter(
            JournalMessage.session_id == session_id,
            JournalMessage.role == "assistant",
        )
        .order_by(JournalMessage.created_at.desc())
        .first()
    )

    analysis = latest_assistant.ai_analysis_json if latest_assistant else None
    behaviors = {}
    ai_inferred = None
    context_tags = None

    if analysis:
        behaviors = analysis.get("factors", {})
        ai_inferred = analysis.get("inferred_dimensions")
        context_tags = analysis.get("context_tags")

    # 3. Upsert DailyCheckIn for backward compatibility
    checkin_date = session.started_at.date()
    checkin = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.checkin_date == checkin_date,
    ).first()

    if checkin:
        checkin.overall_wellbeing = score
        checkin.notes = combined_notes
        checkin.word_count = word_count
        checkin.behaviors_json = behaviors
        checkin.ai_inferred_json = ai_inferred
        checkin.context_tags_json = context_tags
        checkin.depth_level = 3  # Chat is always depth 3
        checkin.updated_at = now
    else:
        checkin = DailyCheckIn(
            user_id=user_id,
            checkin_date=checkin_date,
            overall_wellbeing=score,
            notes=combined_notes,
            word_count=word_count,
            behaviors_json=behaviors,
            ai_inferred_json=ai_inferred,
            context_tags_json=context_tags,
            depth_level=3,
            created_at=now,
            updated_at=now,
        )
        db.add(checkin)

    db.flush()

    # 4. Run wellness score computation
    try:
        from app.engine.wellness_score import compute_wellness_score
        compute_wellness_score(db, user_id, str(checkin_date))
    except Exception as e:
        logger.warning(f"Wellness score computation failed (non-fatal): {e}")

    # 5. Run domain scoring
    try:
        from app.engine.life_domain_scorer import update_domain_scores
        update_domain_scores(db, user_id, checkin)
    except Exception as e:
        logger.warning(f"Domain score update failed (non-fatal): {e}")

    # 6. Trigger milestone detection
    try:
        from app.engine.milestone_detector import detect_milestones
        detect_milestones(db, user_id, checkin_date)
    except Exception as e:
        logger.warning(f"Milestone detection failed (non-fatal): {e}")

    db.commit()

    return {
        "confirmed": True,
        "score": score,
        "date": str(checkin_date),
    }


# ── Session Listing ────────────────────────────────────────────────

def get_sessions_for_user(
    db: Session,
    user_id: int,
    days: int = 30,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get session summaries for the user, most recent first."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    sessions = (
        db.query(JournalSession)
        .filter(
            JournalSession.user_id == user_id,
            JournalSession.started_at >= cutoff,
        )
        .order_by(JournalSession.started_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for s in sessions:
        messages = (
            db.query(JournalMessage)
            .filter(JournalMessage.session_id == s.id)
            .order_by(JournalMessage.created_at.asc())
            .all()
        )

        # First user message as preview
        first_user = next((m for m in messages if m.role == "user"), None)
        preview = ""
        if first_user:
            preview = first_user.content[:100]
            if len(first_user.content) > 100:
                preview += "..."

        results.append({
            "id": s.id,
            "started_at": s.started_at.isoformat() + "Z",
            "daily_score": s.daily_score,
            "message_count": len(messages),
            "preview": preview,
            "summary": s.summary,
        })

    return results


def get_session_messages(
    db: Session,
    user_id: int,
    session_id: int,
) -> List[Dict[str, Any]]:
    """Get all messages for a session in chronological order."""
    # Verify session belongs to user
    session = db.query(JournalSession).filter(
        JournalSession.id == session_id,
        JournalSession.user_id == user_id,
    ).first()

    if not session:
        return []

    messages = (
        db.query(JournalMessage)
        .filter(JournalMessage.session_id == session_id)
        .order_by(JournalMessage.created_at.asc())
        .all()
    )

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() + "Z",
        }
        for m in messages
    ]
