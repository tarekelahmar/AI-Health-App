"""
Domain Check-in Service — weekly explicit life domain ratings.

Handles:
- Checking if a domain check-in is due (>7 days since last)
- Saving a domain check-in (upsert by date)
- Applying explicit scores to LifeDomainScore via EMA (alpha=0.5)
- Retrieving check-in history
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.domain.models.domain_checkin import DomainCheckin
from app.engine.domain_mapping import expand_to_backend_scores
from app.engine.life_domain_scorer import apply_explicit_domain_scores

logger = logging.getLogger(__name__)

CHECKIN_INTERVAL_DAYS = 7


def get_domain_checkin_status(db: Session, user_id: int) -> Dict:
    """
    Check whether a weekly domain check-in is due.

    Returns:
        {"due": bool, "last_checkin_date": str | None, "days_since": int | None}
    """
    latest = (
        db.query(DomainCheckin)
        .filter(DomainCheckin.user_id == user_id)
        .order_by(DomainCheckin.checkin_date.desc())
        .first()
    )

    if not latest:
        return {"due": True, "last_checkin_date": None, "days_since": None}

    last_date = date.fromisoformat(latest.checkin_date)
    days_since = (date.today() - last_date).days

    return {
        "due": days_since >= CHECKIN_INTERVAL_DAYS,
        "last_checkin_date": latest.checkin_date,
        "days_since": days_since,
    }


def save_domain_checkin(
    db: Session,
    user_id: int,
    session_id: Optional[int],
    scores: Dict[str, float],
) -> DomainCheckin:
    """
    Save (upsert) a weekly domain check-in and update EMA scores.

    Args:
        db: Database session.
        user_id: User ID.
        session_id: Optional journal session ID.
        scores: {user_facing_key: score} e.g. {"career": 7.5, ...}.

    Returns:
        The DomainCheckin row.
    """
    today = date.today().isoformat()

    # Upsert: check for existing checkin today
    checkin = (
        db.query(DomainCheckin)
        .filter(
            DomainCheckin.user_id == user_id,
            DomainCheckin.checkin_date == today,
        )
        .first()
    )

    if checkin:
        # Update existing
        checkin.session_id = session_id
        checkin.career = scores.get("career", checkin.career)
        checkin.relationship = scores.get("relationship", checkin.relationship)
        checkin.social = scores.get("social", checkin.social)
        checkin.health = scores.get("health", checkin.health)
        checkin.finance = scores.get("finance", checkin.finance)
    else:
        # Create new
        checkin = DomainCheckin(
            user_id=user_id,
            session_id=session_id,
            checkin_date=today,
            career=scores["career"],
            relationship=scores["relationship"],
            social=scores["social"],
            health=scores["health"],
            finance=scores["finance"],
            created_at=datetime.utcnow(),
        )
        db.add(checkin)

    db.flush()

    # Apply to LifeDomainScore via EMA (1:1 mapping, alpha=0.5)
    backend_scores = expand_to_backend_scores(scores)
    try:
        apply_explicit_domain_scores(db, user_id, backend_scores)
    except Exception:
        logger.exception(
            f"Failed to apply explicit domain scores for user={user_id}"
        )
        # Don't fail the whole operation — the checkin is still saved
        db.commit()

    logger.info(f"Domain check-in saved for user={user_id} date={today}")

    return checkin


def get_domain_checkin_history(
    db: Session,
    user_id: int,
    weeks: int = 12,
) -> List[Dict]:
    """
    Get recent domain check-in history.

    Args:
        db: Database session.
        user_id: User ID.
        weeks: How many weeks of history to return.

    Returns:
        List of dicts with check-in data, most recent first.
    """
    cutoff = (date.today() - timedelta(weeks=weeks)).isoformat()

    checkins = (
        db.query(DomainCheckin)
        .filter(
            DomainCheckin.user_id == user_id,
            DomainCheckin.checkin_date >= cutoff,
        )
        .order_by(DomainCheckin.checkin_date.desc())
        .all()
    )

    return [
        {
            "id": c.id,
            "checkin_date": c.checkin_date,
            "career": c.career,
            "relationship": c.relationship,
            "social": c.social,
            "health": c.health,
            "finance": c.finance,
        }
        for c in checkins
    ]
