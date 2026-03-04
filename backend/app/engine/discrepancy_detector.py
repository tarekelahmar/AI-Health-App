"""
Discrepancy Detector — deterministic rules that flag when journal data is internally inconsistent.

All decisions are rule-based. The detector takes LLM-inferred sentiment as *input*
but never calls an LLM itself. Four independent checks:

1. Slider vs text sentiment: high overall_wellbeing but negative sentiment (or vice versa)
2. Consecutive drops: 3+ day decline in overall_wellbeing
3. Assessment vs behaviour: text mentions motivation/plans but no action tags
4. Values vs reality: high connection slider but prolonged isolation in context tags

Each rule returns an optional Discrepancy; the top-level `detect()` aggregates them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Thresholds (configurable constants) ────────────────────────────

# Rule 1: slider vs text
WELLBEING_HIGH_THRESHOLD = 7.0      # Slider score considered "high"
WELLBEING_LOW_THRESHOLD = 4.0       # Slider score considered "low"
SENTIMENT_NEGATIVE_THRESHOLD = -0.2  # Sentiment below this is negative
SENTIMENT_POSITIVE_THRESHOLD = 0.2   # Sentiment above this is positive

# Rule 2: consecutive drops
CONSECUTIVE_DROP_DAYS = 3           # Minimum consecutive declining days

# Rule 3: assessment vs behaviour
MOTIVATION_KEYWORDS = [
    "going to", "plan to", "want to", "need to", "should",
    "motivated", "determined", "committed", "excited about",
    "looking forward", "ready to", "goal",
]

# Rule 4: connection vs isolation
CONNECTION_HIGH_THRESHOLD = 7.0     # Connection slider considered "high"
ISOLATION_DAYS_THRESHOLD = 3        # Days of isolation to flag


@dataclass
class Discrepancy:
    """A single detected discrepancy."""
    rule: str           # "slider_vs_text", "consecutive_drops", "assessment_vs_behaviour", "connection_vs_isolation"
    flag: bool          # Always True (only created when flagged)
    description: str    # Human-readable explanation
    severity: str       # "info" | "notable" | "significant"


@dataclass
class DiscrepancyResult:
    """Aggregated result from all discrepancy checks."""
    flagged: bool
    discrepancies: List[Discrepancy]

    def to_json(self) -> Optional[Dict]:
        """Serialize for storage in discrepancy_json column."""
        if not self.flagged:
            return None
        return {
            "flag": True,
            "discrepancies": [asdict(d) for d in self.discrepancies],
        }


# ── Rule 1: Slider vs Text Sentiment ──────────────────────────────

def check_slider_vs_text(
    overall_wellbeing: Optional[float],
    sentiment_score: Optional[float],
) -> Optional[Discrepancy]:
    """
    Flag when slider score and text sentiment disagree.
    High slider + negative sentiment → possible avoidance/minimisation.
    Low slider + positive sentiment → possible catastrophising or delayed processing.
    """
    if overall_wellbeing is None or sentiment_score is None:
        return None

    # High wellbeing but negative text
    if overall_wellbeing >= WELLBEING_HIGH_THRESHOLD and sentiment_score < SENTIMENT_NEGATIVE_THRESHOLD:
        return Discrepancy(
            rule="slider_vs_text",
            flag=True,
            description=(
                f"Your wellbeing score ({overall_wellbeing:.1f}) suggests a good day, "
                f"but your writing has a more negative tone. Sometimes we rate how we "
                f"think we should feel rather than how we actually feel."
            ),
            severity="notable",
        )

    # Low wellbeing but positive text
    if overall_wellbeing <= WELLBEING_LOW_THRESHOLD and sentiment_score > SENTIMENT_POSITIVE_THRESHOLD:
        return Discrepancy(
            rule="slider_vs_text",
            flag=True,
            description=(
                f"Your wellbeing score ({overall_wellbeing:.1f}) is low, but your writing "
                f"reads more positively. This gap can happen when there's a specific "
                f"stressor weighing you down that didn't come through in the text."
            ),
            severity="info",
        )

    return None


# ── Rule 2: Consecutive Drops ─────────────────────────────────────

def check_consecutive_drops(
    recent_wellbeing: List[Optional[float]],
    min_days: int = CONSECUTIVE_DROP_DAYS,
) -> Optional[Discrepancy]:
    """
    Flag when overall_wellbeing has declined for min_days+ consecutive days.

    recent_wellbeing: list of scores ordered oldest→newest (most recent last).
    None values break the streak.
    """
    if len(recent_wellbeing) < min_days + 1:
        return None

    # Filter to non-None values with their positions
    valid = [(i, v) for i, v in enumerate(recent_wellbeing) if v is not None]
    if len(valid) < min_days + 1:
        return None

    # Check consecutive decline in the last N+1 valid entries
    # Walk backwards from the end
    consecutive_drops = 0
    for i in range(len(valid) - 1, 0, -1):
        if valid[i][1] < valid[i - 1][1]:
            consecutive_drops += 1
        else:
            break

    if consecutive_drops >= min_days:
        start_val = valid[-(consecutive_drops + 1)][1]
        end_val = valid[-1][1]
        return Discrepancy(
            rule="consecutive_drops",
            flag=True,
            description=(
                f"Your wellbeing has declined for {consecutive_drops} consecutive days "
                f"(from {start_val:.1f} to {end_val:.1f}). Multi-day declines often "
                f"signal something that needs attention."
            ),
            severity="significant" if consecutive_drops >= 5 else "notable",
        )

    return None


# ── Rule 3: Assessment vs Behaviour ───────────────────────────────

def check_assessment_vs_behaviour(
    entry_text: Optional[str],
    context_tags: Optional[Dict],
) -> Optional[Discrepancy]:
    """
    Flag when text mentions motivation/plans but context tags show no
    corresponding action (no exercise, no achievement, etc.).
    """
    if not entry_text or not context_tags:
        return None

    text_lower = entry_text.lower()

    # Check for motivational language in text
    motivation_count = sum(1 for kw in MOTIVATION_KEYWORDS if kw in text_lower)
    if motivation_count < 2:
        return None  # Not enough motivational language to flag

    # Check for action tags
    has_action = (
        context_tags.get("exercise") is True
        or context_tags.get("achievement") is True
        or context_tags.get("work_type") in ("productive", "creative", "deep_work")
    )

    if not has_action:
        return Discrepancy(
            rule="assessment_vs_behaviour",
            flag=True,
            description=(
                "Your entry mentions plans and motivation, but today's activities "
                "don't reflect that yet. This is common — noticing the gap is the "
                "first step to closing it."
            ),
            severity="info",
        )

    return None


# ── Rule 4: Connection vs Isolation ───────────────────────────────

def check_connection_vs_isolation(
    connection_score: Optional[float],
    recent_social_tags: List[Optional[str]],
) -> Optional[Discrepancy]:
    """
    Flag when connection slider is high but recent context tags show
    prolonged isolation (social_contact == "alone" or absent for 3+ days).

    recent_social_tags: social_contact values ordered oldest→newest.
    None means no data for that day.
    """
    if connection_score is None or connection_score < CONNECTION_HIGH_THRESHOLD:
        return None

    if len(recent_social_tags) < ISOLATION_DAYS_THRESHOLD:
        return None

    # Count recent isolation days (last N entries)
    recent = recent_social_tags[-ISOLATION_DAYS_THRESHOLD:]
    isolation_days = sum(
        1 for tag in recent
        if tag is None or tag == "alone" or tag == "none"
    )

    if isolation_days >= ISOLATION_DAYS_THRESHOLD:
        return Discrepancy(
            rule="connection_vs_isolation",
            flag=True,
            description=(
                f"You rated connection at {connection_score:.1f}, but your recent "
                f"entries show limited social contact for the past {isolation_days} "
                f"days. Sometimes we rate aspirational connection rather than actual."
            ),
            severity="notable",
        )

    return None


# ── Top-Level Aggregator ──────────────────────────────────────────

def detect(
    *,
    overall_wellbeing: Optional[float] = None,
    connection_score: Optional[float] = None,
    sentiment_score: Optional[float] = None,
    entry_text: Optional[str] = None,
    context_tags: Optional[Dict] = None,
    recent_wellbeing: Optional[List[Optional[float]]] = None,
    recent_social_tags: Optional[List[Optional[str]]] = None,
) -> DiscrepancyResult:
    """
    Run all discrepancy checks and return aggregated result.

    All parameters are optional — rules that lack data are silently skipped.
    """
    discrepancies: List[Discrepancy] = []

    # Rule 1
    d = check_slider_vs_text(overall_wellbeing, sentiment_score)
    if d:
        discrepancies.append(d)

    # Rule 2
    if recent_wellbeing:
        d = check_consecutive_drops(recent_wellbeing)
        if d:
            discrepancies.append(d)

    # Rule 3
    d = check_assessment_vs_behaviour(entry_text, context_tags)
    if d:
        discrepancies.append(d)

    # Rule 4
    if recent_social_tags:
        d = check_connection_vs_isolation(connection_score, recent_social_tags)
        if d:
            discrepancies.append(d)

    return DiscrepancyResult(
        flagged=len(discrepancies) > 0,
        discrepancies=discrepancies,
    )
