"""
Milestone Detector — deterministic detection of user achievements.

Five milestone types:
1. score_streak:       5+ consecutive days above personal average
2. recovery:           score climbs 3+ points after a dip
3. pattern_confirmed:  first pattern reaches confirmed status
4. consistency:        14+ consecutive real entry days
5. domain_improvement: any life domain +2 points over 30 days

All detection is deterministic (no LLM). Called after check-in save.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.models.daily_checkin import DailyCheckIn
from app.domain.models.milestone import Milestone

logger = logging.getLogger(__name__)


@dataclass
class DetectedMilestone:
    milestone_type: str
    description: str
    category: str
    metadata: dict = field(default_factory=dict)


def _is_real_entry(entry: DailyCheckIn) -> bool:
    """Distinguish real entries from auto-created placeholder rows."""
    return (
        entry.overall_wellbeing is not None
        or (entry.word_count is not None and entry.word_count > 0)
    )


def _get_recent_real_entries(
    db: Session, user_id: int, days: int = 30
) -> List[DailyCheckIn]:
    """Fetch recent real entries ordered by date descending."""
    cutoff = date.today() - timedelta(days=days)
    entries = (
        db.query(DailyCheckIn)
        .filter(
            DailyCheckIn.user_id == user_id,
            DailyCheckIn.checkin_date >= cutoff,
        )
        .order_by(DailyCheckIn.checkin_date.desc())
        .all()
    )
    return [e for e in entries if _is_real_entry(e)]


def check_score_streak(entries: List[DailyCheckIn], threshold: int = 5) -> Optional[DetectedMilestone]:
    """5+ consecutive days with overall_wellbeing above personal average."""
    scores = [e.overall_wellbeing for e in entries if e.overall_wellbeing is not None]
    if len(scores) < threshold:
        return None

    avg = sum(scores) / len(scores)
    # entries are newest-first; check consecutive run from most recent
    streak = 0
    for score in scores:
        if score >= avg:
            streak += 1
        else:
            break

    if streak >= threshold:
        return DetectedMilestone(
            milestone_type="score_streak",
            description=f"{streak}-day streak above your average ({avg:.1f})",
            category="achievement",
            metadata={"streak_days": streak, "average": round(avg, 1)},
        )
    return None


def check_recovery(entries: List[DailyCheckIn], climb_threshold: float = 3.0) -> Optional[DetectedMilestone]:
    """Score climbs 3+ points after a dip (comparing today vs lowest in last 7 days)."""
    scores = [e.overall_wellbeing for e in entries if e.overall_wellbeing is not None]
    if len(scores) < 3:
        return None

    current = scores[0]  # newest
    recent_window = scores[1:8]  # last 7 before today
    if not recent_window:
        return None

    trough = min(recent_window)
    if current - trough >= climb_threshold:
        return DetectedMilestone(
            milestone_type="recovery",
            description=f"Recovered {current - trough:.1f} points from recent low of {trough:.1f}",
            category="progress",
            metadata={"current": current, "trough": trough, "climb": round(current - trough, 1)},
        )
    return None


def check_pattern_confirmed(db: Session, user_id: int) -> Optional[DetectedMilestone]:
    """First pattern reaches confirmed status."""
    try:
        from app.engine.memory.pattern_manager import PatternManager
        mgr = PatternManager(db)
        patterns = mgr.get_active_patterns(user_id=user_id)
        confirmed = [p for p in patterns if p.status == "confirmed"]
        if confirmed:
            # Check if we already logged this milestone
            existing = (
                db.query(Milestone)
                .filter(
                    Milestone.user_id == user_id,
                    Milestone.milestone_type == "pattern_confirmed",
                )
                .first()
            )
            if existing:
                return None  # Already detected

            name = (confirmed[0].relationship_json or {}).get("pattern_name", "pattern")
            return DetectedMilestone(
                milestone_type="pattern_confirmed",
                description=f"First confirmed pattern: {name}",
                category="achievement",
                metadata={"pattern_name": name, "total_confirmed": len(confirmed)},
            )
    except Exception as e:
        logger.warning(f"Pattern milestone check failed: {e}")
    return None


def check_consistency(entries: List[DailyCheckIn], threshold: int = 14) -> Optional[DetectedMilestone]:
    """14+ consecutive real entry days."""
    if len(entries) < threshold:
        return None

    # Build set of dates with real entries
    entry_dates = sorted({e.checkin_date for e in entries}, reverse=True)
    if not entry_dates:
        return None

    # Count consecutive days from most recent
    streak = 1
    for i in range(1, len(entry_dates)):
        if (entry_dates[i - 1] - entry_dates[i]).days == 1:
            streak += 1
        else:
            break

    if streak >= threshold:
        return DetectedMilestone(
            milestone_type="consistency",
            description=f"{streak} consecutive days of journaling",
            category="consistency",
            metadata={"streak_days": streak},
        )
    return None


def check_domain_improvement(
    db: Session, user_id: int, threshold: float = 2.0
) -> Optional[DetectedMilestone]:
    """Any life domain +2 points over 30 days."""
    try:
        from app.domain.models.life_domain_score import LifeDomainScore, LIFE_DOMAINS, LIFE_DOMAIN_LABELS

        today_str = str(date.today())
        ago_str = str(date.today() - timedelta(days=30))

        current = (
            db.query(LifeDomainScore)
            .filter(LifeDomainScore.user_id == user_id, LifeDomainScore.score_date == today_str)
            .first()
        )
        past = (
            db.query(LifeDomainScore)
            .filter(LifeDomainScore.user_id == user_id, LifeDomainScore.score_date <= ago_str)
            .order_by(LifeDomainScore.score_date.desc())
            .first()
        )

        if not current or not past:
            return None

        current_scores = current.get_scores()
        past_scores = past.get_scores()

        best_domain = None
        best_improvement = 0.0
        for domain in LIFE_DOMAINS:
            c = current_scores.get(domain, 5.0)
            p = past_scores.get(domain, 5.0)
            improvement = c - p
            if improvement > best_improvement:
                best_improvement = improvement
                best_domain = domain

        if best_improvement >= threshold and best_domain:
            label = LIFE_DOMAIN_LABELS.get(best_domain, best_domain)
            return DetectedMilestone(
                milestone_type="domain_improvement",
                description=f"{label} improved by {best_improvement:.1f} points over 30 days",
                category="progress",
                metadata={
                    "domain": best_domain,
                    "improvement": round(best_improvement, 1),
                    "current": round(current_scores.get(best_domain, 5.0), 1),
                },
            )
    except Exception as e:
        logger.warning(f"Domain improvement check failed: {e}")
    return None


def detect_milestones(db: Session, user_id: int) -> List[DetectedMilestone]:
    """
    Run all milestone checks and return newly detected milestones.

    Called after check-in save. Persists new milestones to DB.
    """
    entries = _get_recent_real_entries(db, user_id, days=30)

    detected: List[DetectedMilestone] = []

    # Run each check
    for check_fn in [
        lambda: check_score_streak(entries),
        lambda: check_recovery(entries),
        lambda: check_pattern_confirmed(db, user_id),
        lambda: check_consistency(entries),
        lambda: check_domain_improvement(db, user_id),
    ]:
        try:
            result = check_fn()
            if result:
                detected.append(result)
        except Exception as e:
            logger.warning(f"Milestone check failed: {e}")

    # Persist new milestones (skip duplicates via unique constraint)
    today = date.today()
    persisted = []
    for m in detected:
        # Check if already exists today
        existing = (
            db.query(Milestone)
            .filter(
                Milestone.user_id == user_id,
                Milestone.milestone_type == m.milestone_type,
                Milestone.detected_date == today,
            )
            .first()
        )
        if not existing:
            import json
            from datetime import datetime
            row = Milestone(
                user_id=user_id,
                milestone_type=m.milestone_type,
                detected_date=today,
                description=m.description,
                category=m.category,
                metadata_json=json.dumps(m.metadata),
                created_at=datetime.utcnow(),
            )
            db.add(row)
            persisted.append(m)

    if persisted:
        db.commit()
        logger.info(f"Detected {len(persisted)} new milestones for user {user_id}")

    return detected


def get_user_milestones(db: Session, user_id: int, limit: int = 20) -> List[Milestone]:
    """Fetch recent milestones for display."""
    return (
        db.query(Milestone)
        .filter(Milestone.user_id == user_id)
        .order_by(Milestone.detected_date.desc())
        .limit(limit)
        .all()
    )
