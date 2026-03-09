"""
Life Domain Scorer — EMA-based 10-axis life satisfaction scoring.

After each journal entry, the companion infers which life domains
are relevant and at what implicit score. This service applies
an Exponential Moving Average to update domain scores smoothly.

Rules:
- Only update domains mentioned in the entry (untouched domains carry forward)
- Cold start: all domains at 5.0
- EMA alpha = 0.3 (configurable)
- Scores clamped to 1.0-10.0
- Slider-derived signals (direct mapping) override companion-inferred signals
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.domain.models.daily_checkin import DailyCheckIn
from app.domain.models.life_domain_score import (
    DEFAULT_SCORE,
    LIFE_DOMAINS,
    LifeDomainScore,
)

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────

EMA_ALPHA = 0.3  # Weight of new observation vs history

# Slider → life domain mappings (direct, high confidence)
SLIDER_DOMAIN_MAP: Dict[str, Dict[str, float]] = {
    # slider_key: {domain: weight}
    "overall_wellbeing": {"mental_emotional": 0.6, "purpose_meaning": 0.4},
    "energy": {"physical_health": 0.8, "structure_routine": 0.2},
    "mood": {"mental_emotional": 0.7, "social_friendships": 0.3},
    "focus": {"career_work": 0.5, "structure_routine": 0.3, "growth_learning": 0.2},
    "connection": {"relationship": 0.4, "social_friendships": 0.6},
}

# Context tag → life domain mappings
CONTEXT_TAG_DOMAIN_MAP: Dict[str, Dict[str, float]] = {
    "exercise": {"physical_health": 7.0},  # Exercise presence implies decent physical health
    "social_contact:friends": {"social_friendships": 7.5},
    "social_contact:family": {"relationship": 7.0},
    "social_contact:partner": {"relationship": 8.0},
    "social_contact:alone": {"social_friendships": 3.5},
    "work_type:productive": {"career_work": 7.5, "structure_routine": 7.0},
    "work_type:creative": {"career_work": 7.0, "growth_learning": 7.5},
    "work_type:stressful": {"career_work": 4.0},
    "achievement": {"career_work": 8.0, "purpose_meaning": 7.5},
    "conflict": {"relationship": 3.5, "mental_emotional": 4.0},
}


# ── Core EMA Logic ────────────────────────────────────────────────

def ema_update(previous: float, signal: float, alpha: float = EMA_ALPHA) -> float:
    """Apply exponential moving average update."""
    new = alpha * signal + (1 - alpha) * previous
    return max(1.0, min(10.0, new))


def _derive_signals_from_sliders(checkin: DailyCheckIn) -> Dict[str, float]:
    """
    Map slider scores to life domain signals.

    Each slider contributes to 1-3 domains with weighted influence.
    Slider range is 1.0-10.0, which maps directly to domain score range.
    """
    signals: Dict[str, list] = {d: [] for d in LIFE_DOMAINS}

    for slider_key, domain_weights in SLIDER_DOMAIN_MAP.items():
        value = getattr(checkin, slider_key, None)
        if value is None:
            continue
        for domain, weight in domain_weights.items():
            signals[domain].append((value, weight))

    # Weighted average for each domain
    result: Dict[str, float] = {}
    for domain, weighted_values in signals.items():
        if not weighted_values:
            continue
        total_weight = sum(w for _, w in weighted_values)
        weighted_sum = sum(v * w for v, w in weighted_values)
        result[domain] = weighted_sum / total_weight

    return result


def _derive_signals_from_context_tags(context_tags: Optional[Dict]) -> Dict[str, float]:
    """
    Map context tags to life domain signals.

    Context tags provide boolean/categorical signals that map to
    approximate domain scores.
    """
    if not context_tags:
        return {}

    signals: Dict[str, list] = {d: [] for d in LIFE_DOMAINS}

    for tag_key, domain_scores in CONTEXT_TAG_DOMAIN_MAP.items():
        if ":" in tag_key:
            # Compound key like "social_contact:friends"
            base_key, expected_value = tag_key.split(":", 1)
            actual_value = context_tags.get(base_key)
            if actual_value != expected_value:
                continue
        else:
            # Simple boolean tag
            if not context_tags.get(tag_key):
                continue

        for domain, score in domain_scores.items():
            signals[domain].append(score)

    # Average signals per domain
    result: Dict[str, float] = {}
    for domain, scores in signals.items():
        if scores:
            result[domain] = sum(scores) / len(scores)

    return result


def _derive_signals_from_companion(ai_inferred: Optional[Dict]) -> Dict[str, float]:
    """
    Map companion-inferred dimensions to life domain signals.

    These are secondary signals — slider-derived signals take precedence.
    """
    if not ai_inferred:
        return {}

    # Dimension → domain mapping
    mapping = {
        "motivation": {"purpose_meaning": 0.6, "career_work": 0.4},
        "self_worth": {"mental_emotional": 0.7, "purpose_meaning": 0.3},
        "structure_adherence": {"structure_routine": 0.8, "career_work": 0.2},
        "emotional_regulation": {"mental_emotional": 0.8, "relationship": 0.2},
        "relationship_quality": {"relationship": 0.7, "social_friendships": 0.3},
    }

    signals: Dict[str, list] = {d: [] for d in LIFE_DOMAINS}

    for dim_key, domain_weights in mapping.items():
        value = ai_inferred.get(dim_key)
        if value is None:
            continue
        for domain, weight in domain_weights.items():
            signals[domain].append((value, weight))

    result: Dict[str, float] = {}
    for domain, weighted_values in signals.items():
        if not weighted_values:
            continue
        total_weight = sum(w for _, w in weighted_values)
        weighted_sum = sum(v * w for v, w in weighted_values)
        result[domain] = weighted_sum / total_weight

    return result


# ── Main Service Function ─────────────────────────────────────────

def update_life_domain_scores(
    db: Session,
    user_id: int,
    checkin: DailyCheckIn,
) -> LifeDomainScore:
    """
    Update life domain scores for a user after a journal entry.

    Signal priority (highest to lowest):
    1. Slider-derived (direct, most reliable)
    2. Context tag-derived (situational)
    3. Companion-inferred (interpretive, secondary)

    Only domains with signals are updated. Others carry forward.
    """
    score_date = str(checkin.checkin_date)

    # Load or create today's score row
    score_row = db.query(LifeDomainScore).filter(
        LifeDomainScore.user_id == user_id,
        LifeDomainScore.score_date == score_date,
    ).first()

    if not score_row:
        # Look for most recent previous score to carry forward
        prev = (
            db.query(LifeDomainScore)
            .filter(LifeDomainScore.user_id == user_id)
            .order_by(LifeDomainScore.score_date.desc())
            .first()
        )

        score_row = LifeDomainScore(
            user_id=user_id,
            score_date=score_date,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        if prev:
            # Carry forward all previous scores
            for domain in LIFE_DOMAINS:
                setattr(score_row, domain, getattr(prev, domain))

        db.add(score_row)

    # Gather signals from all sources
    slider_signals = _derive_signals_from_sliders(checkin)
    context_signals = _derive_signals_from_context_tags(
        checkin.context_tags_json if isinstance(checkin.context_tags_json, dict) else None
    )
    companion_signals = _derive_signals_from_companion(
        checkin.ai_inferred_json if isinstance(checkin.ai_inferred_json, dict) else None
    )

    # Merge signals (priority: slider > context > companion)
    merged: Dict[str, float] = {}
    derivation: Dict[str, Dict] = {}

    for domain in LIFE_DOMAINS:
        if domain in slider_signals:
            merged[domain] = slider_signals[domain]
            derivation[domain] = {"signal_source": "slider_mapped", "confidence": 0.9}
        elif domain in context_signals:
            merged[domain] = context_signals[domain]
            derivation[domain] = {"signal_source": "context_tag", "confidence": 0.7}
        elif domain in companion_signals:
            merged[domain] = companion_signals[domain]
            derivation[domain] = {"signal_source": "companion_inferred", "confidence": 0.5}

    # Apply EMA updates
    for domain, signal in merged.items():
        previous = getattr(score_row, domain)
        new_score = ema_update(previous, signal)
        score_row.set_score(domain, new_score)

    score_row.derivation_json = json.dumps(derivation) if derivation else None
    score_row.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(score_row)

    logger.info(
        f"Life domain scores updated for user={user_id} date={score_date}: "
        f"{len(merged)} domains updated, total={score_row.total_score:.1f}/100"
    )

    return score_row


# ── Explicit Domain Check-in Update ──────────────────────────────

EXPLICIT_ALPHA = 0.5  # Stronger weight for user's direct ratings

def apply_explicit_domain_scores(
    db: Session,
    user_id: int,
    domain_scores: Dict[str, float],
    alpha: float = EXPLICIT_ALPHA,
) -> LifeDomainScore:
    """
    Apply explicit user domain ratings via EMA.

    Unlike update_life_domain_scores() which derives signals from
    DailyCheckIn sliders/tags/companion, this takes raw backend-column
    domain scores directly (from the weekly domain check-in card).

    Uses a higher alpha (0.5) than the implicit 0.3, because the user's
    direct rating is a stronger, more intentional signal.

    Args:
        db: Database session.
        user_id: User ID.
        domain_scores: {backend_column_name: score} e.g. {"career_work": 7.5}.
        alpha: EMA weight for the explicit signal. Default 0.5.

    Returns:
        Updated LifeDomainScore row.
    """
    score_date = date.today().isoformat()

    # Load or create today's score row
    score_row = db.query(LifeDomainScore).filter(
        LifeDomainScore.user_id == user_id,
        LifeDomainScore.score_date == score_date,
    ).first()

    if not score_row:
        # Carry forward from most recent
        prev = (
            db.query(LifeDomainScore)
            .filter(LifeDomainScore.user_id == user_id)
            .order_by(LifeDomainScore.score_date.desc())
            .first()
        )

        score_row = LifeDomainScore(
            user_id=user_id,
            score_date=score_date,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        if prev:
            for domain in LIFE_DOMAINS:
                setattr(score_row, domain, getattr(prev, domain))
        else:
            # Cold start: explicitly set defaults (SQLAlchemy defaults don't apply in-memory)
            for domain in LIFE_DOMAINS:
                setattr(score_row, domain, DEFAULT_SCORE)

        db.add(score_row)

    # Apply EMA updates for provided domains only
    derivation: Dict[str, Dict] = {}
    for domain, signal in domain_scores.items():
        if domain not in LIFE_DOMAINS:
            logger.warning(f"Unknown domain '{domain}' in explicit scores, skipping")
            continue
        previous = getattr(score_row, domain, DEFAULT_SCORE) or DEFAULT_SCORE
        new_score = ema_update(previous, signal, alpha=alpha)
        score_row.set_score(domain, new_score)
        derivation[domain] = {"signal_source": "explicit_checkin", "confidence": 1.0}

    # Merge with existing derivation if present
    existing_derivation = {}
    if score_row.derivation_json:
        try:
            existing_derivation = json.loads(score_row.derivation_json) if isinstance(score_row.derivation_json, str) else score_row.derivation_json
        except (json.JSONDecodeError, TypeError):
            pass
    existing_derivation.update(derivation)
    score_row.derivation_json = json.dumps(existing_derivation)
    score_row.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(score_row)

    logger.info(
        f"Explicit domain scores applied for user={user_id} date={score_date}: "
        f"{len(domain_scores)} domains updated, total={score_row.total_score:.1f}/100"
    )

    return score_row
