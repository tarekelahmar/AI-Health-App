"""
Journal Companion Service — single LLM call that combines:

1. Factor extraction (folded in from llm/factor_extraction.py)
2. Dimension inference (motivation, anxiety, self_worth, etc.)
3. Context tag inference (exercise, social_contact, work_type, etc.)
4. Companion response generation (acknowledgment, pattern observation, question)

The companion is the accumulative observer: it sees recent entries, confirmed
patterns, and domain trajectories, then generates a response that builds on
everything it knows about the user.

When LLM is disabled, returns a deterministic-only result (no companion text,
no inferred dimensions, but factor extraction falls back to None).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.domain.models.daily_checkin import DailyCheckIn
from app.engine.discrepancy_detector import detect as detect_discrepancies, DiscrepancyResult
from app.engine.prompts.journal_companion_system import build_system_prompt
from app.llm.factor_extraction import KNOWN_FACTORS, FACTOR_KEYS

logger = logging.getLogger(__name__)


# ── Result Dataclasses ────────────────────────────────────────────

@dataclass
class InferredDimensions:
    motivation: Optional[float] = None
    anxiety_level: Optional[float] = None
    self_worth: Optional[float] = None
    structure_adherence: Optional[float] = None
    emotional_regulation: Optional[float] = None
    relationship_quality: Optional[float] = None
    sentiment_score: float = 0.0
    inferred_overall: Optional[float] = None


@dataclass
class ContextTags:
    exercise: Optional[bool] = None
    exercise_type: Optional[str] = None
    social_contact: Optional[str] = None
    work_type: Optional[str] = None
    sleep: Optional[str] = None
    substances: Optional[str] = None
    location: Optional[str] = None
    conflict: Optional[bool] = None
    conflict_with: Optional[str] = None
    achievement: Optional[bool] = None
    achievement_note: Optional[str] = None


@dataclass
class CompanionResponseText:
    text: str = ""
    pattern_referenced: bool = False
    discrepancy_noted: bool = False


@dataclass
class CompanionResult:
    """Full result from the companion service."""
    extraction_method: str  # "llm" | "deterministic_only"
    factors: Dict[str, Any] = field(default_factory=dict)
    custom_factors: List[Dict[str, Any]] = field(default_factory=list)
    inferred_dimensions: Optional[InferredDimensions] = None
    context_tags: Optional[ContextTags] = None
    companion_response: Optional[CompanionResponseText] = None
    discrepancies: Optional[DiscrepancyResult] = None
    depth_level: int = 2


# ── Context Assembly ──────────────────────────────────────────────

def _format_recent_entries(entries: List[DailyCheckIn], max_entries: int = 7) -> str:
    """Format recent entries for the LLM context window."""
    if not entries:
        return "No previous entries."

    lines = ["RECENT ENTRIES (newest first):"]
    for entry in entries[:max_entries]:
        scores = []
        if entry.overall_wellbeing is not None:
            scores.append(f"Wellbeing={entry.overall_wellbeing}")
        if entry.energy is not None:
            scores.append(f"Energy={entry.energy}")
        if entry.mood is not None:
            scores.append(f"Mood={entry.mood}")
        if entry.focus is not None:
            scores.append(f"Focus={entry.focus}")
        if entry.connection is not None:
            scores.append(f"Connection={entry.connection}")

        score_str = ", ".join(scores) if scores else "no scores"
        notes_preview = ""
        if entry.notes:
            notes_preview = entry.notes[:200]
            if len(entry.notes) > 200:
                notes_preview += "..."

        lines.append(
            f"  [{entry.checkin_date}] {score_str}"
            + (f"\n    \"{notes_preview}\"" if notes_preview else "")
        )

    return "\n".join(lines)


def _format_active_patterns(db: Session, user_id: int) -> str:
    """Format active patterns from the pattern manager."""
    try:
        from app.engine.memory.pattern_manager import PatternManager
        mgr = PatternManager(db)
        patterns = mgr.get_active_patterns(user_id=user_id)

        if not patterns:
            return "No confirmed patterns yet."

        lines = ["ACTIVE PATTERNS:"]
        for p in patterns:
            rel = p.relationship_json or {}
            name = rel.get("pattern_name", p.pattern_type)
            desc = rel.get("description", "")
            confidence = p.current_confidence
            status = p.status
            lines.append(f"  - [{status}] {name} (confidence: {confidence:.0%}): {desc}")

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Could not load patterns for companion context: {e}")
        return "Pattern data unavailable."


def _format_rolling_summary(db: Session, user_id: int) -> str:
    """Build a condensed rolling summary of the user's journal history."""
    try:
        entries = (
            db.query(DailyCheckIn)
            .filter(DailyCheckIn.user_id == user_id)
            .filter(DailyCheckIn.overall_wellbeing.isnot(None))  # Only real V2 entries
            .order_by(DailyCheckIn.checkin_date.desc())
            .all()
        )

        if not entries:
            return "New user — no history yet."

        total = len(entries)
        date_range = f"{entries[-1].checkin_date} to {entries[0].checkin_date}"

        # Compute averages
        wellbeing_vals = [e.overall_wellbeing for e in entries if e.overall_wellbeing is not None]
        avg_wellbeing = sum(wellbeing_vals) / len(wellbeing_vals) if wellbeing_vals else 0

        # Recent trend (last 7 vs previous 7)
        recent_7 = wellbeing_vals[:7]
        prev_7 = wellbeing_vals[7:14]
        trend = ""
        if recent_7 and prev_7:
            recent_avg = sum(recent_7) / len(recent_7)
            prev_avg = sum(prev_7) / len(prev_7)
            diff = recent_avg - prev_avg
            if diff > 0.5:
                trend = f"Trending UP (+{diff:.1f} vs previous week)"
            elif diff < -0.5:
                trend = f"Trending DOWN ({diff:.1f} vs previous week)"
            else:
                trend = "Stable (similar to previous week)"

        lines = [
            "USER SUMMARY:",
            f"  Total V2 entries: {total}",
            f"  Date range: {date_range}",
            f"  Average wellbeing: {avg_wellbeing:.1f}/10",
        ]
        if trend:
            lines.append(f"  Trajectory: {trend}")

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Could not build rolling summary: {e}")
        return "Summary unavailable."


def _format_today_factors(db: Session, user_id: int) -> str:
    """Format today's behavioral factors for companion context.

    Two-tier loading:
    1. Check DailyCheckIn.behaviors_json (populated after score confirmation)
    2. Fallback: check latest session's assistant messages for ai_analysis_json.factors
       (populated mid-conversation by _run_analysis(), before score confirmation)

    Without the fallback, the companion would always say "No factors tracked"
    during the conversation — defeating the purpose of action awareness.
    """
    from datetime import datetime as dt

    today = date.today()
    behaviors: Optional[Dict] = None

    # Tier 1: DailyCheckIn (populated after score confirmation)
    checkin = (
        db.query(DailyCheckIn)
        .filter(
            DailyCheckIn.user_id == user_id,
            DailyCheckIn.checkin_date == today,
        )
        .first()
    )
    if checkin and checkin.behaviors_json:
        behaviors = checkin.behaviors_json

    # Tier 2: Latest session's analysis (populated mid-conversation)
    if not behaviors:
        try:
            from app.domain.models.journal_session import JournalSession
            from app.domain.models.journal_message import JournalMessage

            today_start = dt.combine(today, dt.min.time())
            latest_session = (
                db.query(JournalSession)
                .filter(
                    JournalSession.user_id == user_id,
                    JournalSession.started_at >= today_start,
                )
                .order_by(JournalSession.started_at.desc())
                .first()
            )

            if latest_session:
                latest_msg = (
                    db.query(JournalMessage)
                    .filter(
                        JournalMessage.session_id == latest_session.id,
                        JournalMessage.role == "assistant",
                        JournalMessage.ai_analysis_json.isnot(None),
                    )
                    .order_by(JournalMessage.created_at.desc())
                    .first()
                )
                if latest_msg and latest_msg.ai_analysis_json:
                    behaviors = latest_msg.ai_analysis_json.get("factors", {})
        except Exception as e:
            logger.warning(f"Could not load session factors for today: {e}")

    if not behaviors:
        return "No behavioral factors tracked today yet."

    done = [k.replace("_", " ").title() for k, v in behaviors.items() if v is True]
    skipped = [k.replace("_", " ").title() for k, v in behaviors.items() if v is False]

    lines = ["TODAY'S BEHAVIORAL FACTORS:"]
    if done:
        lines.append(f"  Done: {', '.join(done)}")
    if skipped:
        lines.append(f"  Not done: {', '.join(skipped)}")
    if not done and not skipped:
        lines.append("  No boolean factors extracted yet.")

    return "\n".join(lines)


def _get_recent_entries(db: Session, user_id: int, days: int = 14) -> List[DailyCheckIn]:
    """Fetch recent check-in entries for context."""
    cutoff = date.today() - timedelta(days=days)
    return (
        db.query(DailyCheckIn)
        .filter(
            DailyCheckIn.user_id == user_id,
            DailyCheckIn.checkin_date >= cutoff,
        )
        .order_by(DailyCheckIn.checkin_date.desc())
        .all()
    )


# ── LLM Call ──────────────────────────────────────────────────────

def _call_companion_llm(
    system_prompt: str,
    entry_text: str,
    slider_scores: Dict[str, float],
    entry_date: str,
) -> Optional[Dict]:
    """
    Make the single LLM call for companion analysis.

    Returns parsed JSON dict or None on failure.
    """
    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed — companion unavailable")
        return None

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — companion unavailable")
        return None

    # Build the user message with today's entry injected
    user_message = (
        f"Today's entry ({entry_date}):\n"
        f"Scores: Overall Wellbeing={slider_scores.get('overall_wellbeing', 'N/A')}, "
        f"Energy={slider_scores.get('energy', 'N/A')}, "
        f"Mood={slider_scores.get('mood', 'N/A')}, "
        f"Focus={slider_scores.get('focus', 'N/A')}, "
        f"Connection={slider_scores.get('connection', 'N/A')}\n\n"
        f"Journal text:\n---\n{entry_text[:3000] if entry_text else '(no text)'}\n---\n\n"
        f"Respond in the JSON format specified in your instructions."
    )

    # Companion needs a stronger model than factor extraction for tone/pattern quality
    model = os.getenv("ANTHROPIC_COMPANION_MODEL", os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250514"))

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        content = response.content[0].text if response.content else None
        if not content:
            logger.warning("Companion LLM returned empty response")
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
        logger.error(f"Companion: invalid JSON from LLM: {e}")
        return None
    except Exception as e:
        logger.error(f"Companion LLM call failed: {e}")
        return None


# ── Governance Validation ─────────────────────────────────────────

# Forbidden language in companion responses (superset of claim policy)
FORBIDDEN_PHRASES = [
    "diagnos", "prescri", "medicat", "disease", "disorder", "syndrome",
    "treatment plan", "therapy session", "you have", "you suffer",
    "causes", "proves", "cures", "guarantees", "always works",
    "at least it", "at least you", "it could be worse", "just try to",
]


def _validate_companion_text(text: str) -> Optional[str]:
    """
    Validate companion response text against governance rules.

    Returns cleaned text or None if validation fails (fail-closed).
    """
    if not text or not text.strip():
        return None

    text_lower = text.lower()
    violations = []
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text_lower:
            violations.append(phrase)

    if violations:
        logger.warning(f"Companion text failed governance: {violations}")
        return None  # Fail closed — drop the response

    return text.strip()


# ── Factor Filtering (reused from factor_extraction.py) ───────────

BLOCKED_FACTOR_TERMS = {
    "diagnos", "prescri", "medicat", "disease", "disorder",
    "syndrome", "treatment", "therapy", "symptom",
}


def _clean_factors(raw_factors: Dict[str, Any]) -> Dict[str, Any]:
    """Filter factors to known vocabulary only."""
    return {k: v for k, v in raw_factors.items() if k in KNOWN_FACTORS}


def _clean_custom_factors(raw_custom: List[Dict]) -> List[Dict]:
    """Filter custom factors: reject medical/diagnostic terms, cap at 5."""
    clean = []
    for cf in raw_custom:
        label = cf.get("label", "").lower()
        key = cf.get("key", "").lower()
        if not any(term in label or term in key for term in BLOCKED_FACTOR_TERMS):
            clean.append(cf)
    return clean[:5]


# ── Main Service Function ────────────────────────────────────────

def _resolve_depth_level(
    db: Session, user_id: int, explicit_depth: Optional[int], word_count: Optional[int]
) -> int:
    """
    Resolve the effective depth level.

    Priority: explicit param > user preference > adaptive from word count > default (2).
    """
    if explicit_depth is not None:
        return max(1, min(3, explicit_depth))

    # Try loading from user preferences
    try:
        from app.domain.models.user_preference import UserPreference
        pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        if pref and pref.preferred_depth_level:
            return pref.preferred_depth_level
    except Exception:
        pass

    # Adaptive: word count hint
    if word_count is not None:
        if word_count >= 200:
            return 3
        if word_count < 50:
            return 1

    return 2  # default


def generate_companion_response(
    db: Session,
    user_id: int,
    checkin: DailyCheckIn,
    depth_level: int = None,
) -> CompanionResult:
    """
    Generate a full companion response for a journal entry.

    This is the single entry point that:
    1. Gathers context (recent entries, patterns, summary)
    2. Calls LLM if enabled (combined factor extraction + inference + response)
    3. Runs deterministic discrepancy detection
    4. Validates companion text against governance rules
    5. Returns CompanionResult

    When LLM is disabled, returns deterministic-only result.
    """
    # Resolve depth level from preferences / word count / explicit param
    depth_level = _resolve_depth_level(db, user_id, depth_level, checkin.word_count)

    slider_scores = {
        "overall_wellbeing": checkin.overall_wellbeing,
        "energy": checkin.energy,
        "mood": checkin.mood,
        "focus": checkin.focus,
        "connection": checkin.connection,
    }

    # ── 1. Check if LLM is enabled ───────────────────────────────
    enable_llm = os.getenv("ENABLE_LLM_TRANSLATION", "false").lower() == "true"

    if not enable_llm:
        logger.info("LLM disabled — companion returning deterministic-only result")
        return CompanionResult(
            extraction_method="deterministic_only",
            depth_level=depth_level,
        )

    # ── 2. Gather context ────────────────────────────────────────
    recent_entries = _get_recent_entries(db, user_id)
    # Exclude today's entry from context (it's the one being analysed)
    context_entries = [
        e for e in recent_entries
        if e.checkin_date != checkin.checkin_date
    ]

    recent_entries_text = _format_recent_entries(context_entries)
    active_patterns_text = _format_active_patterns(db, user_id)
    rolling_summary_text = _format_rolling_summary(db, user_id)

    factor_keys_text = ", ".join(FACTOR_KEYS)

    system_prompt = build_system_prompt(
        depth_level=depth_level,
        active_patterns_text=active_patterns_text,
        recent_entries_text=recent_entries_text,
        rolling_summary_text=rolling_summary_text,
        factor_keys_text=factor_keys_text,
    )

    # ── 3. LLM call ─────────────────────────────────────────────
    llm_result = _call_companion_llm(
        system_prompt=system_prompt,
        entry_text=checkin.notes or "",
        slider_scores={k: v for k, v in slider_scores.items() if v is not None},
        entry_date=str(checkin.checkin_date),
    )

    if llm_result is None:
        # LLM call failed — return deterministic-only
        return CompanionResult(
            extraction_method="deterministic_only",
            depth_level=depth_level,
        )

    # ── 4. Parse LLM output ─────────────────────────────────────
    # Inferred dimensions
    inferred_raw = llm_result.get("inferred_dimensions", {})
    inferred = InferredDimensions(
        motivation=inferred_raw.get("motivation"),
        anxiety_level=inferred_raw.get("anxiety_level"),
        self_worth=inferred_raw.get("self_worth"),
        structure_adherence=inferred_raw.get("structure_adherence"),
        emotional_regulation=inferred_raw.get("emotional_regulation"),
        relationship_quality=inferred_raw.get("relationship_quality"),
        sentiment_score=inferred_raw.get("sentiment_score", 0.0),
        inferred_overall=inferred_raw.get("inferred_overall"),
    )

    # Context tags
    tags_raw = llm_result.get("context_tags", {})
    context_tags = ContextTags(
        exercise=tags_raw.get("exercise"),
        exercise_type=tags_raw.get("exercise_type"),
        social_contact=tags_raw.get("social_contact"),
        work_type=tags_raw.get("work_type"),
        sleep=tags_raw.get("sleep"),
        substances=tags_raw.get("substances"),
        location=tags_raw.get("location"),
        conflict=tags_raw.get("conflict"),
        conflict_with=tags_raw.get("conflict_with"),
        achievement=tags_raw.get("achievement"),
        achievement_note=tags_raw.get("achievement_note"),
    )

    # Factors (consolidated — replaces standalone factor extraction)
    factors = _clean_factors(llm_result.get("factors", {}))
    custom_factors = _clean_custom_factors(llm_result.get("custom_factors", []))

    # Companion response text
    response_raw = llm_result.get("response", {})
    response_text = response_raw.get("text", "")

    # ── 5. Governance validation ─────────────────────────────────
    validated_text = _validate_companion_text(response_text)

    companion_response = CompanionResponseText(
        text=validated_text or "",
        pattern_referenced=response_raw.get("pattern_referenced", False),
        discrepancy_noted=response_raw.get("discrepancy_noted", False),
    )

    # ── 6. Deterministic discrepancy detection ───────────────────
    # Build recent wellbeing list for consecutive drops check
    recent_wellbeing = []
    for e in reversed(context_entries):  # oldest first
        recent_wellbeing.append(e.overall_wellbeing)
    # Append today's score at the end
    recent_wellbeing.append(checkin.overall_wellbeing)

    # Build recent social tags for connection/isolation check
    recent_social_tags = []
    for e in reversed(context_entries):
        tags = e.context_tags_json or {}
        recent_social_tags.append(tags.get("social_contact"))
    # Append today's inferred tag
    recent_social_tags.append(context_tags.social_contact)

    discrepancy_result = detect_discrepancies(
        overall_wellbeing=checkin.overall_wellbeing,
        connection_score=checkin.connection,
        sentiment_score=inferred.sentiment_score,
        entry_text=checkin.notes,
        context_tags=asdict(context_tags),
        recent_wellbeing=recent_wellbeing,
        recent_social_tags=recent_social_tags,
    )

    # ── 7. Assemble result ───────────────────────────────────────
    return CompanionResult(
        extraction_method="llm",
        factors=factors,
        custom_factors=custom_factors,
        inferred_dimensions=inferred,
        context_tags=context_tags,
        companion_response=companion_response,
        discrepancies=discrepancy_result,
        depth_level=depth_level,
    )
