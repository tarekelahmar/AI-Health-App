from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.domain.repositories.insight_repository import InsightRepository
from app.domain.repositories.evaluation_repository import EvaluationRepository
from app.domain.repositories.daily_checkin_repository import DailyCheckInRepository
from app.domain.repositories.adherence_repository import AdherenceRepository
from app.domain.repositories.narrative_repository import NarrativeRepository
from app.domain.repositories.personal_driver_repository import PersonalDriverRepository

# Optional LLM translation layer (safe): reuse your existing pattern if present
try:
    from app.llm.client import translate_insight  # type: ignore
except Exception:
    translate_insight = None  # noqa: N816


@dataclass
class NarrativeDraft:
    title: str
    summary: str
    key_points: List[Any]
    drivers: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    risks: List[Dict[str, Any]]
    metadata: Dict[str, Any]


def _to_dt(d: date, end: bool = False) -> datetime:
    if end:
        return datetime(d.year, d.month, d.day, 23, 59, 59)
    return datetime(d.year, d.month, d.day, 0, 0, 0)


def _pick_top(items: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    return items[:k]


def synthesize_narrative(
    db: Session,
    *,
    user_id: int,
    period_type: str,
    start: date,
    end: date,
    include_llm_translation: bool = False,
) -> NarrativeDraft:
    insight_repo = InsightRepository(db)
    eval_repo = EvaluationRepository(db)
    checkin_repo = DailyCheckInRepository(db)
    adherence_repo = AdherenceRepository(db)

    # Pull core signals (keep this deterministic & explainable)
    # Insights: assume repo can list_by_user; if not, adapt to yours.
    insights = insight_repo.list_by_user(user_id=user_id, limit=200)

    # Filter insights generated within range (created_at / generated_at)
    in_range = []
    for it in insights:
        ts = getattr(it, "generated_at", None) or getattr(it, "created_at", None)
        if ts is None:
            continue
        if _to_dt(start) <= ts <= _to_dt(end, end=True):
            in_range.append(it)

    evaluations = eval_repo.list_by_user(user_id=user_id, limit=50)
    eval_in_range = []
    for ev in evaluations:
        ts = getattr(ev, "created_at", None)
        if ts and _to_dt(start) <= ts <= _to_dt(end, end=True):
            eval_in_range.append(ev)

    # Daily checkins in range
    try:
        checkins = checkin_repo.list_range(user_id=user_id, start_date=start, end_date=end)
    except AttributeError:
        # Fallback: get individual checkins and filter
        all_checkins = checkin_repo.list_by_user(user_id=user_id, limit=100)
        checkins = []
        for c in all_checkins:
            checkin_date = getattr(c, "checkin_date", None)
            if checkin_date and start <= checkin_date <= end:
                checkins.append(c)

    # Adherence events in range (if your repo supports it)
    try:
        adherence = adherence_repo.list_range(user_id=user_id, start_date=start, end_date=end)
    except (AttributeError, Exception):
        # Fallback: get via experiments
        adherence = []

    # Pull personal drivers (STEP T integration)
    personal_driver_repo = PersonalDriverRepository(db)
    personal_drivers = personal_driver_repo.list_for_user(user_id=user_id, limit=50)
    
    # Build drivers from insights evidence + personal drivers
    drivers = []
    risks = []
    
    # Add personal drivers to key points
    window_days = (end - start).days + 1
    for pd in personal_drivers[:10]:  # Top 10 personal drivers
        if pd.confidence >= 0.6:  # Only high-confidence drivers
            direction_text = "improves" if pd.direction == "positive" else "worsens" if pd.direction == "negative" else "affects"
            lag_text = f" (with {pd.lag_days} day lag)" if pd.lag_days > 0 else ""
            drivers.append({
                "metric_key": pd.outcome_metric,
                "why": f"{pd.driver_key.replace('_', ' ')} {direction_text} {pd.outcome_metric.replace('_', ' ')}{lag_text}",
                "type": "personal_driver",
                "confidence": pd.confidence,
                "effect_size": pd.effect_size,
                "variance_explained": pd.variance_explained,
                "driver_key": pd.driver_key,
            })
    
    for it in in_range[:50]:
        meta = {}
        try:
            metadata_str = getattr(it, "metadata_json", None) or "{}"
            if isinstance(metadata_str, str):
                import json
                meta = json.loads(metadata_str)
            elif isinstance(metadata_str, dict):
                meta = metadata_str
        except Exception:
            meta = {}
        metric_key = meta.get("metric_key") or getattr(it, "metric_key", None)
        confidence = getattr(it, "confidence_score", None) or meta.get("confidence")
        typ = meta.get("type") or getattr(it, "insight_type", None) or "insight"

        # Safety surfaced
        safety = meta.get("safety")
        if isinstance(safety, dict) and safety.get("risk_level") in ("high", "moderate"):
            risks.append(
                {
                    "risk": safety.get("headline", "Safety note"),
                    "guidance": safety.get("guidance", "Review this carefully."),
                    "metric_key": metric_key,
                }
            )

        drivers.append(
            {
                "metric_key": metric_key,
                "why": getattr(it, "title", "Change detected"),
                "type": typ,
                "confidence": float(confidence) if confidence is not None else None,
                "evidence": meta,
            }
        )

    # Actions: from evaluations + adherence gaps + checkins
    actions = []
    for ev in eval_in_range[:10]:
        actions.append(
            {
                "action": "Continue" if getattr(ev, "verdict", "") == "helpful" else "Review",
                "rationale": f"Experiment verdict: {getattr(ev, 'verdict', 'unknown')}",
                "metric_key": getattr(ev, "metric_key", None),
                "safety": getattr(ev, "details_json", None),
            }
        )

    # If user didn't check in much, prompt
    expected_days = (end - start).days + 1
    coverage = len(checkins) / expected_days if expected_days > 0 else 0.0
    if coverage < 0.5:
        actions.append(
            {
                "action": "Complete daily check-ins",
                "rationale": "Your subjective signals help explain wearable/lab changes and make evaluations more reliable.",
                "metric_key": None,
                "safety": None,
            }
        )

    # Simple key points (human-readable bullets, deterministic)
    key_points = []
    if not in_range and not personal_drivers:
        key_points.append("No notable changes detected in this period.")
    else:
        # Prioritize personal drivers in key points
        top_personal = [d for d in drivers if d.get("type") == "personal_driver"][:3]
        top_insights = [d for d in drivers if d.get("type") != "personal_driver"][:2]
        
        for d in top_personal + top_insights:
            mk = d.get("metric_key") or "metric"
            why = d.get("why", "Change detected")
            key_points.append(f"{mk}: {why}")
        
        # Add personal driver summary if available
        if personal_drivers:
            top_positive = [pd for pd in personal_drivers if pd.direction == "positive"][:1]
            if top_positive:
                pd = top_positive[0]
                key_points.insert(0, f"Over the last {window_days} days, {pd.driver_key.replace('_', ' ')} appears to be your strongest driver of {pd.outcome_metric.replace('_', ' ')}.")

    # Summary/title
    if period_type == "daily":
        title = f"Daily summary — {start.isoformat()}"
    else:
        title = f"Weekly summary — {start.isoformat()} to {end.isoformat()}"

    summary = (
        f"{len(in_range)} insights generated. "
        f"{len(eval_in_range)} experiment evaluations. "
        f"Check-in coverage: {int(coverage * 100)}%."
    )

    metadata = {
        "insights_count": len(in_range),
        "evaluations_count": len(eval_in_range),
        "checkins_count": len(checkins),
        "checkin_coverage": coverage,
        "adherence_events_count": len(adherence),
    }

    # Optional: LLM translation of the narrative summary ONLY (not decisions)
    # Keep it safe and gated
    if include_llm_translation and translate_insight is not None:
        try:
            # Reuse your translate_insight as a generic "plain-language" function if it exists.
            # If not suitable, keep deterministic.
            pass
        except Exception:
            pass

    return NarrativeDraft(
        title=title,
        summary=summary,
        key_points=key_points,
        drivers=drivers[:25],
        actions=actions[:10],
        risks=risks[:10],
        metadata=metadata,
    )


def generate_and_persist_narrative(
    db: Session,
    *,
    user_id: int,
    period_type: str,
    start: date,
    end: date,
    include_llm_translation: bool = False,
):
    repo = NarrativeRepository(db)
    draft = synthesize_narrative(
        db,
        user_id=user_id,
        period_type=period_type,
        start=start,
        end=end,
        include_llm_translation=include_llm_translation,
    )
    return repo.upsert(
        user_id=user_id,
        period_type=period_type,
        period_start=start,
        period_end=end,
        title=draft.title,
        summary=draft.summary,
        key_points_json=draft.key_points,
        drivers_json=draft.drivers,
        actions_json=draft.actions,
        risks_json=draft.risks,
        metadata_json=draft.metadata,
    )

