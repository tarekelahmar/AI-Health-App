"""
Journal Synthesis — weekly and monthly synthesis cards.

Weekly: avg scores, trend, top pattern observation, domain movement, one question.
Monthly: everything in weekly + phase narrative, domain radar comparison,
         top 3 patterns, focus recommendations.

Deterministic template core (works without LLM).
LLM enhancement: natural language narrative wrapping the data (optional).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.domain.models.daily_checkin import DailyCheckIn
from app.domain.models.life_domain_score import LifeDomainScore, LIFE_DOMAINS, LIFE_DOMAIN_LABELS

logger = logging.getLogger(__name__)


# ── Phase Classification ───────────────────────────────────────────

PHASES = ["CRISIS", "STABILIZING", "BUILDING", "STABLE", "GROWING"]


@dataclass
class PhaseClassification:
    phase: str  # One of PHASES
    confidence: float  # 0.0-1.0 based on entry count
    description: str


def classify_phase(
    scores: List[float],
    entry_count: int,
) -> PhaseClassification:
    """
    Classify a week into a life phase based on score trajectory and volatility.

    Conservative: defaults to STABILIZING over CRISIS, STABLE over GROWING.
    """
    if not scores or entry_count == 0:
        return PhaseClassification("STABLE", 0.0, "Insufficient data")

    avg = sum(scores) / len(scores)
    variance = sum((s - avg) ** 2 for s in scores) / len(scores)
    volatility = variance ** 0.5
    confidence = min(1.0, entry_count / 5.0)  # full confidence at 5+ entries/week

    # Trend: first half vs second half
    mid = len(scores) // 2
    if mid > 0:
        first_half = sum(scores[:mid]) / mid
        second_half = sum(scores[mid:]) / max(1, len(scores) - mid)
        trend = second_half - first_half
    else:
        trend = 0.0

    # Classification rules (conservative)
    if avg < 3.0 and volatility > 2.0:
        phase = "CRISIS"
        desc = "High instability and low scores"
    elif avg < 4.5 or volatility > 2.5:
        phase = "STABILIZING"
        desc = "Working towards stability"
    elif trend > 1.0 and avg >= 6.0 and volatility < 1.5:
        phase = "GROWING"
        desc = "Upward trajectory with low volatility"
    elif avg >= 5.5 and volatility < 2.0:
        phase = "STABLE"
        desc = "Consistent scores, steady state"
    elif trend > 0.5:
        phase = "BUILDING"
        desc = "Building momentum"
    else:
        phase = "STABILIZING"
        desc = "Working towards stability"

    return PhaseClassification(phase, confidence, desc)


# ── Data Structures ───────────────────────────────────────────────

@dataclass
class WeeklySynthesis:
    week_start: str
    week_end: str
    entry_count: int
    avg_wellbeing: Optional[float]
    avg_energy: Optional[float]
    avg_mood: Optional[float]
    score_range: tuple  # (min, max)
    trend: str  # "up", "down", "stable"
    phase: PhaseClassification
    top_pattern: Optional[str]
    domain_changes: Dict[str, float]  # domain -> delta
    companion_question: Optional[str]  # LLM-generated or template

    def to_dict(self) -> dict:
        return {
            "week_start": self.week_start,
            "week_end": self.week_end,
            "entry_count": self.entry_count,
            "avg_wellbeing": self.avg_wellbeing,
            "avg_energy": self.avg_energy,
            "avg_mood": self.avg_mood,
            "score_range": list(self.score_range),
            "trend": self.trend,
            "phase": {"phase": self.phase.phase, "confidence": self.phase.confidence, "description": self.phase.description},
            "top_pattern": self.top_pattern,
            "domain_changes": self.domain_changes,
            "companion_question": self.companion_question,
        }


@dataclass
class MonthlySynthesis:
    month: str  # "2026-02"
    entry_count: int
    avg_wellbeing: Optional[float]
    score_range: tuple
    weekly_phases: List[dict]
    top_patterns: List[str]
    domain_start: Dict[str, float]
    domain_end: Dict[str, float]
    milestones: List[str]
    phase_narrative: Optional[str]  # LLM-generated or template
    focus_areas: List[str]  # LLM-generated or template

    def to_dict(self) -> dict:
        return {
            "month": self.month,
            "entry_count": self.entry_count,
            "avg_wellbeing": self.avg_wellbeing,
            "score_range": list(self.score_range),
            "weekly_phases": self.weekly_phases,
            "top_patterns": self.top_patterns,
            "domain_start": self.domain_start,
            "domain_end": self.domain_end,
            "milestones": self.milestones,
            "phase_narrative": self.phase_narrative,
            "focus_areas": self.focus_areas,
        }


# ── Weekly Synthesis ──────────────────────────────────────────────

def generate_weekly_synthesis(
    db: Session,
    user_id: int,
    week_end: date = None,
) -> Optional[WeeklySynthesis]:
    """Generate a weekly synthesis card for the last 7 days."""
    if week_end is None:
        week_end = date.today()
    week_start = week_end - timedelta(days=6)

    entries = (
        db.query(DailyCheckIn)
        .filter(
            DailyCheckIn.user_id == user_id,
            DailyCheckIn.checkin_date >= week_start,
            DailyCheckIn.checkin_date <= week_end,
            DailyCheckIn.overall_wellbeing.isnot(None),
        )
        .order_by(DailyCheckIn.checkin_date.asc())
        .all()
    )

    if not entries:
        return None

    wellbeing = [e.overall_wellbeing for e in entries if e.overall_wellbeing is not None]
    energy = [e.energy for e in entries if e.energy is not None]
    mood = [e.mood for e in entries if e.mood is not None]

    avg_w = sum(wellbeing) / len(wellbeing) if wellbeing else None
    avg_e = sum(energy) / len(energy) if energy else None
    avg_m = sum(mood) / len(mood) if mood else None
    score_range = (min(wellbeing), max(wellbeing)) if wellbeing else (0, 0)

    # Trend
    if len(wellbeing) >= 4:
        first = sum(wellbeing[:len(wellbeing)//2]) / (len(wellbeing)//2)
        second = sum(wellbeing[len(wellbeing)//2:]) / max(1, len(wellbeing) - len(wellbeing)//2)
        diff = second - first
        trend = "up" if diff > 0.5 else "down" if diff < -0.5 else "stable"
    else:
        trend = "stable"

    # Phase
    phase = classify_phase(wellbeing, len(entries))

    # Top pattern
    top_pattern = _get_top_pattern(db, user_id)

    # Domain changes this week
    domain_changes = _get_domain_changes(db, user_id, week_start, week_end)

    # Companion question (template fallback)
    companion_question = _generate_weekly_question(trend, avg_w, top_pattern)

    return WeeklySynthesis(
        week_start=str(week_start),
        week_end=str(week_end),
        entry_count=len(entries),
        avg_wellbeing=round(avg_w, 1) if avg_w else None,
        avg_energy=round(avg_e, 1) if avg_e else None,
        avg_mood=round(avg_m, 1) if avg_m else None,
        score_range=score_range,
        trend=trend,
        phase=phase,
        top_pattern=top_pattern,
        domain_changes=domain_changes,
        companion_question=companion_question,
    )


# ── Monthly Synthesis ─────────────────────────────────────────────

def generate_monthly_synthesis(
    db: Session,
    user_id: int,
    month_str: str = None,
) -> Optional[MonthlySynthesis]:
    """Generate a monthly synthesis for the given month (e.g., '2026-02')."""
    if month_str is None:
        today = date.today()
        # Default to previous month
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        month_str = last_month_end.strftime("%Y-%m")

    year, month = int(month_str.split("-")[0]), int(month_str.split("-")[1])
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(year, month + 1, 1) - timedelta(days=1)

    entries = (
        db.query(DailyCheckIn)
        .filter(
            DailyCheckIn.user_id == user_id,
            DailyCheckIn.checkin_date >= month_start,
            DailyCheckIn.checkin_date <= month_end,
            DailyCheckIn.overall_wellbeing.isnot(None),
        )
        .order_by(DailyCheckIn.checkin_date.asc())
        .all()
    )

    if not entries:
        return None

    wellbeing = [e.overall_wellbeing for e in entries if e.overall_wellbeing is not None]
    avg_w = sum(wellbeing) / len(wellbeing) if wellbeing else None
    score_range = (min(wellbeing), max(wellbeing)) if wellbeing else (0, 0)

    # Weekly phases
    weekly_phases = []
    current = month_start
    while current <= month_end:
        w_end = min(current + timedelta(days=6), month_end)
        w_entries = [e for e in entries if current <= e.checkin_date <= w_end]
        w_scores = [e.overall_wellbeing for e in w_entries if e.overall_wellbeing is not None]
        phase = classify_phase(w_scores, len(w_entries))
        weekly_phases.append({
            "week_start": str(current),
            "week_end": str(w_end),
            "phase": phase.phase,
            "confidence": phase.confidence,
            "entry_count": len(w_entries),
            "avg": round(sum(w_scores) / len(w_scores), 1) if w_scores else None,
        })
        current = w_end + timedelta(days=1)

    # Top patterns
    top_patterns = _get_top_patterns(db, user_id, limit=3)

    # Domain comparison
    domain_start = _get_domain_snapshot(db, user_id, month_start)
    domain_end = _get_domain_snapshot(db, user_id, month_end)

    # Milestones
    milestones = _get_milestones_for_range(db, user_id, month_start, month_end)

    # Phase narrative (deterministic template)
    phase_narrative = _build_phase_narrative(weekly_phases, avg_w, len(entries))

    # Focus areas (deterministic)
    focus_areas = _identify_focus_areas(domain_end, top_patterns)

    return MonthlySynthesis(
        month=month_str,
        entry_count=len(entries),
        avg_wellbeing=round(avg_w, 1) if avg_w else None,
        score_range=score_range,
        weekly_phases=weekly_phases,
        top_patterns=top_patterns,
        domain_start=domain_start,
        domain_end=domain_end,
        milestones=milestones,
        phase_narrative=phase_narrative,
        focus_areas=focus_areas,
    )


# ── Helpers ───────────────────────────────────────────────────────

def _get_top_pattern(db: Session, user_id: int) -> Optional[str]:
    """Get the top confirmed pattern name."""
    try:
        from app.engine.memory.pattern_manager import PatternManager
        mgr = PatternManager(db)
        patterns = mgr.get_active_patterns(user_id=user_id)
        confirmed = [p for p in patterns if p.status == "confirmed"]
        if confirmed:
            rel = confirmed[0].relationship_json or {}
            return rel.get("pattern_name", confirmed[0].pattern_type)
    except Exception:
        pass
    return None


def _get_top_patterns(db: Session, user_id: int, limit: int = 3) -> List[str]:
    """Get top N pattern names."""
    try:
        from app.engine.memory.pattern_manager import PatternManager
        mgr = PatternManager(db)
        patterns = mgr.get_active_patterns(user_id=user_id)
        result = []
        for p in patterns[:limit]:
            rel = p.relationship_json or {}
            name = rel.get("pattern_name", p.pattern_type)
            result.append(name)
        return result
    except Exception:
        return []


def _get_domain_changes(
    db: Session, user_id: int, week_start: date, week_end: date
) -> Dict[str, float]:
    """Domain score changes over a week."""
    try:
        start = (
            db.query(LifeDomainScore)
            .filter(LifeDomainScore.user_id == user_id, LifeDomainScore.score_date <= str(week_start))
            .order_by(LifeDomainScore.score_date.desc())
            .first()
        )
        end = (
            db.query(LifeDomainScore)
            .filter(LifeDomainScore.user_id == user_id, LifeDomainScore.score_date <= str(week_end))
            .order_by(LifeDomainScore.score_date.desc())
            .first()
        )
        if not start or not end:
            return {}

        s_scores = start.get_scores()
        e_scores = end.get_scores()
        changes = {}
        for d in LIFE_DOMAINS:
            delta = e_scores.get(d, 5.0) - s_scores.get(d, 5.0)
            if abs(delta) >= 0.3:  # Only show meaningful changes
                changes[LIFE_DOMAIN_LABELS.get(d, d)] = round(delta, 1)
        return changes
    except Exception:
        return {}


def _get_domain_snapshot(db: Session, user_id: int, target_date: date) -> Dict[str, float]:
    """Get domain scores closest to a date."""
    try:
        row = (
            db.query(LifeDomainScore)
            .filter(LifeDomainScore.user_id == user_id, LifeDomainScore.score_date <= str(target_date))
            .order_by(LifeDomainScore.score_date.desc())
            .first()
        )
        if row:
            return {LIFE_DOMAIN_LABELS.get(d, d): round(row.get_scores().get(d, 5.0), 1) for d in LIFE_DOMAINS}
    except Exception:
        pass
    return {LIFE_DOMAIN_LABELS.get(d, d): 5.0 for d in LIFE_DOMAINS}


def _get_milestones_for_range(
    db: Session, user_id: int, start: date, end: date
) -> List[str]:
    """Fetch milestone descriptions in a date range."""
    try:
        from app.domain.models.milestone import Milestone
        rows = (
            db.query(Milestone)
            .filter(
                Milestone.user_id == user_id,
                Milestone.detected_date >= start,
                Milestone.detected_date <= end,
            )
            .order_by(Milestone.detected_date.asc())
            .all()
        )
        return [r.description for r in rows]
    except Exception:
        return []


def _generate_weekly_question(
    trend: str, avg_wellbeing: Optional[float], top_pattern: Optional[str]
) -> str:
    """Deterministic question templates based on week data."""
    if trend == "down" and avg_wellbeing and avg_wellbeing < 5:
        return "What's one small thing you could change this week to shift the trajectory?"
    if trend == "up":
        return "What's been working well this week that you want to keep doing?"
    if top_pattern:
        return f"Your '{top_pattern}' pattern was active this week. Did you notice its effect?"
    return "Looking at this week, what stood out to you?"


def _build_phase_narrative(
    weekly_phases: List[dict], avg_wellbeing: Optional[float], entry_count: int
) -> str:
    """Build a deterministic phase narrative from weekly data."""
    if not weekly_phases:
        return "Not enough data for a phase narrative."

    phases = [w["phase"] for w in weekly_phases if w.get("phase")]
    if not phases:
        return "Not enough data for a phase narrative."

    # Dominant phase
    from collections import Counter
    phase_counts = Counter(phases)
    dominant = phase_counts.most_common(1)[0][0]

    # Transitions
    transitions = []
    for i in range(1, len(phases)):
        if phases[i] != phases[i - 1]:
            transitions.append(f"{phases[i - 1]} -> {phases[i]}")

    narrative = f"This month was predominantly {dominant.lower()}"
    if avg_wellbeing:
        narrative += f" with an average wellbeing of {avg_wellbeing:.1f}/10"
    narrative += f" across {entry_count} entries."

    if transitions:
        narrative += f" Phase shifts: {', '.join(transitions)}."

    return narrative


def _identify_focus_areas(
    domain_scores: Dict[str, float], top_patterns: List[str]
) -> List[str]:
    """Identify domains that could use attention."""
    areas = []
    # Find lowest-scoring domains
    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1])
    for name, score in sorted_domains[:2]:
        if score < 6.0:
            areas.append(f"{name} ({score:.1f}/10)")

    if not areas:
        areas.append("All domains are tracking well. Maintain consistency.")

    return areas
