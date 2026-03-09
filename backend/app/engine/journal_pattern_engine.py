"""
Journal Pattern Engine — deterministic pattern detection from behavioral factors × scores.

Discovers named patterns like:
- "Exercise = Floor" (never scored below 6 on exercise days)
- "The Formula" (People + Exercise + Structure = 6+ score)
- "The Crash Pattern" (Isolation + No exercise = crash to 2-4)
- "Meditation Boost" (single factor strongly elevates a metric)

All detection is deterministic — no LLM involved.
Feeds results into existing PatternManager for lifecycle management.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.api.schemas.journal import PatternComputeResponse
from app.domain.models.daily_checkin import DailyCheckIn
from app.domain.repositories.daily_checkin_repository import DailyCheckInRepository

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────

MIN_ENTRIES_FOR_PATTERNS = 7      # Minimum entries with a factor before detecting
MIN_ENTRIES_FOR_CONFIRM = 10      # Minimum before confirming
FLOOR_THRESHOLD = 6               # Score must be >= this for "floor" patterns
HIGH_SCORE_THRESHOLD = 7          # Mean must be >= this for "formula" patterns
LOW_SCORE_THRESHOLD = 4           # Mean must be <= this for "crash" patterns
MIN_EFFECT_SIZE = 0.5             # Minimum Cohen's d for any pattern
STRONG_EFFECT_SIZE = 0.8          # Cohen's d threshold for "boost" patterns
MAX_COMBO_SIZE = 3                # Maximum factors in a combination

# V2 score metrics (1.0-10.0 float scale)
SCORE_METRICS_V2 = ["overall_wellbeing", "energy", "mood", "focus", "connection"]

# V1 score metrics (0-10 int scale, deprecated)
SCORE_METRICS_V1 = ["energy", "mood", "stress", "focus", "sleep_quality"]

# Default: V2 (compute_journal_patterns selects dynamically per entry)
SCORE_METRICS = SCORE_METRICS_V2

# Factors where True is "negative" (for crash detection)
NEGATIVE_FACTORS = {"isolated", "alcohol", "caffeine_late", "late_screen"}

# Pattern name templates
PATTERN_NAMES = {
    "floor": "{factor} = Floor",
    "formula": "The Formula",
    "crash": "The Crash Pattern",
    "boost": "{factor} Boost",
}

PATTERN_ICONS = {
    "floor": "🛡️",
    "formula": "✨",
    "crash": "📉",
    "boost": "🚀",
}


# ── Data Structures ────────────────────────────────────────────────

@dataclass
class JournalPattern:
    """A discovered pattern from journal factors vs. scores."""
    pattern_name: str
    pattern_type: str          # floor | formula | crash | boost
    input_factors: List[str]
    output_metric: str

    # Statistical evidence
    mean_with: float
    mean_without: float
    effect_size: float         # Cohen's d
    n_with: int
    n_without: int
    exceptions: int            # Times pattern didn't hold
    confidence: float

    # Display
    description: str
    icon: str
    data_summary: str


@dataclass
class DayRecord:
    """A single day's factors and scores."""
    checkin_date: date
    factors: Dict[str, Any]
    scores: Dict[str, Optional[float]]


# ── Helpers ────────────────────────────────────────────────────────

def _cohens_d(mean1: float, mean2: float, std1: float, std2: float,
              n1: int, n2: int) -> float:
    """Compute Cohen's d (pooled standard deviation)."""
    if n1 + n2 < 4:
        return 0.0
    pooled_var = ((n1 - 1) * std1 ** 2 + (n2 - 1) * std2 ** 2) / (n1 + n2 - 2)
    pooled_std = math.sqrt(pooled_var) if pooled_var > 0 else 1e-6
    return (mean1 - mean2) / pooled_std


def _std(values: List[float]) -> float:
    """Standard deviation of a list."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def _mean(values: List[float]) -> float:
    """Mean of a list."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _get_boolean_factors(factors: Dict[str, Any]) -> Dict[str, bool]:
    """Extract only boolean factors from a day's behaviors_json."""
    result = {}
    for key, value in factors.items():
        if isinstance(value, bool):
            result[key] = value
        elif value in (0, 1):
            result[key] = bool(value)
    return result


# ── Pattern Detection Functions ────────────────────────────────────

def _detect_floor_patterns(
    days: List[DayRecord],
    metric: str,
) -> List[JournalPattern]:
    """Detect floor patterns: factor presence guarantees score >= threshold."""
    patterns = []
    all_factors = _collect_all_boolean_factors(days)

    for factor in all_factors:
        # Get scores when factor is True
        with_scores = [
            d.scores[metric] for d in days
            if d.factors.get(factor) is True and d.scores.get(metric) is not None
        ]
        without_scores = [
            d.scores[metric] for d in days
            if d.factors.get(factor) is not True and d.scores.get(metric) is not None
        ]

        if len(with_scores) < MIN_ENTRIES_FOR_PATTERNS or len(without_scores) < 3:
            continue

        min_with = min(with_scores)
        exceptions = sum(1 for s in with_scores if s < FLOOR_THRESHOLD)
        mean_with = _mean(with_scores)
        mean_without = _mean(without_scores)

        # Floor: min score with factor >= threshold, and meaningfully higher than without
        if min_with >= FLOOR_THRESHOLD and exceptions <= 1:
            effect = _cohens_d(
                mean_with, mean_without,
                _std(with_scores), _std(without_scores),
                len(with_scores), len(without_scores),
            )
            if effect < MIN_EFFECT_SIZE:
                continue

            factor_label = factor.replace("_", " ").title()
            confidence = min(0.9, 0.4 + (len(with_scores) / 30) * 0.5)

            patterns.append(JournalPattern(
                pattern_name=PATTERN_NAMES["floor"].format(factor=factor_label),
                pattern_type="floor",
                input_factors=[factor],
                output_metric=metric,
                mean_with=round(mean_with, 1),
                mean_without=round(mean_without, 1),
                effect_size=round(effect, 2),
                n_with=len(with_scores),
                n_without=len(without_scores),
                exceptions=exceptions,
                confidence=round(confidence, 2),
                description=(
                    f"Never scored below {FLOOR_THRESHOLD} on a {factor_label.lower()} day. "
                    f"Average {mean_with:.1f} vs {mean_without:.1f} without."
                ),
                icon=PATTERN_ICONS["floor"],
                data_summary=f"{len(with_scores)} days with, avg {mean_with:.1f} vs {mean_without:.1f}",
            ))

    return patterns


def _detect_formula_patterns(
    days: List[DayRecord],
    metric: str,
) -> List[JournalPattern]:
    """Detect formula patterns: combination of factors predicts consistently high scores."""
    patterns = []
    all_factors = _collect_all_boolean_factors(days)

    # Only consider factors that individually show a positive signal
    positive_factors = []
    for factor in all_factors:
        if factor in NEGATIVE_FACTORS:
            continue
        with_scores = [
            d.scores[metric] for d in days
            if d.factors.get(factor) is True and d.scores.get(metric) is not None
        ]
        without_scores = [
            d.scores[metric] for d in days
            if d.factors.get(factor) is not True and d.scores.get(metric) is not None
        ]
        if len(with_scores) >= 3 and _mean(with_scores) > _mean(without_scores):
            positive_factors.append(factor)

    # Test combinations of 2-3 positive factors
    for combo_size in (2, 3):
        if len(positive_factors) < combo_size:
            continue

        for combo in combinations(positive_factors, combo_size):
            combo_list = list(combo)

            # Days where ALL factors in combo are True
            with_scores = [
                d.scores[metric] for d in days
                if all(d.factors.get(f) is True for f in combo_list)
                and d.scores.get(metric) is not None
            ]
            # Days where NONE of the factors are True
            without_scores = [
                d.scores[metric] for d in days
                if all(d.factors.get(f) is not True for f in combo_list)
                and d.scores.get(metric) is not None
            ]

            if len(with_scores) < MIN_ENTRIES_FOR_PATTERNS or len(without_scores) < 3:
                continue

            mean_with = _mean(with_scores)
            mean_without = _mean(without_scores)
            std_with = _std(with_scores)

            if mean_with < HIGH_SCORE_THRESHOLD:
                continue

            effect = _cohens_d(
                mean_with, mean_without,
                std_with, _std(without_scores),
                len(with_scores), len(without_scores),
            )
            if effect < STRONG_EFFECT_SIZE:
                continue

            exceptions = sum(1 for s in with_scores if s < FLOOR_THRESHOLD)
            confidence = min(0.9, 0.4 + (len(with_scores) / 25) * 0.5)

            labels = [f.replace("_", " ").title() for f in combo_list]
            formula_str = " + ".join(labels)

            patterns.append(JournalPattern(
                pattern_name="The Formula" if combo_size == 3 else f"{formula_str} Formula",
                pattern_type="formula",
                input_factors=combo_list,
                output_metric=metric,
                mean_with=round(mean_with, 1),
                mean_without=round(mean_without, 1),
                effect_size=round(effect, 2),
                n_with=len(with_scores),
                n_without=len(without_scores),
                exceptions=exceptions,
                confidence=round(confidence, 2),
                description=(
                    f"{formula_str} = {mean_with:.0f}+ {metric}. "
                    f"{exceptions} exceptions in {len(with_scores)} days."
                ),
                icon=PATTERN_ICONS["formula"],
                data_summary=f"{len(with_scores)} combo days, avg {mean_with:.1f} vs {mean_without:.1f}",
            ))

    return patterns


def _detect_crash_patterns(
    days: List[DayRecord],
    metric: str,
) -> List[JournalPattern]:
    """Detect crash patterns: negative factor combinations predict low scores."""
    patterns = []

    # Negative indicators: factors in NEGATIVE_FACTORS that are True,
    # or positive factors that are False
    # We look for: isolated=True AND exercised=False patterns
    all_factors = _collect_all_boolean_factors(days)

    negative_indicators = []
    for factor in all_factors:
        if factor in NEGATIVE_FACTORS:
            negative_indicators.append((factor, True))
        elif factor in {"exercised", "social_contact", "structured_day"}:
            negative_indicators.append((factor, False))

    # Test combos of 2-3 negative indicators
    for combo_size in (2, 3):
        if len(negative_indicators) < combo_size:
            continue

        for combo in combinations(negative_indicators, combo_size):
            combo_list = list(combo)

            with_scores = [
                d.scores[metric] for d in days
                if all(d.factors.get(f) == v for f, v in combo_list)
                and d.scores.get(metric) is not None
            ]
            without_scores = [
                d.scores[metric] for d in days
                if not all(d.factors.get(f) == v for f, v in combo_list)
                and d.scores.get(metric) is not None
            ]

            if len(with_scores) < MIN_ENTRIES_FOR_PATTERNS or len(without_scores) < 3:
                continue

            mean_with = _mean(with_scores)
            mean_without = _mean(without_scores)

            if mean_with > LOW_SCORE_THRESHOLD:
                continue

            effect = _cohens_d(
                mean_without, mean_with,  # Reversed: "without" negative factors is better
                _std(without_scores), _std(with_scores),
                len(without_scores), len(with_scores),
            )
            if effect < MIN_EFFECT_SIZE:
                continue

            confidence = min(0.9, 0.4 + (len(with_scores) / 20) * 0.5)

            # Build description
            parts = []
            for f, v in combo_list:
                label = f.replace("_", " ").title()
                if v is False:
                    parts.append(f"No {label}")
                else:
                    parts.append(label)
            crash_str = " + ".join(parts)
            factor_keys = [f for f, _ in combo_list]

            patterns.append(JournalPattern(
                pattern_name="The Crash Pattern",
                pattern_type="crash",
                input_factors=factor_keys,
                output_metric=metric,
                mean_with=round(mean_with, 1),
                mean_without=round(mean_without, 1),
                effect_size=round(effect, 2),
                n_with=len(with_scores),
                n_without=len(without_scores),
                exceptions=0,
                confidence=round(confidence, 2),
                description=(
                    f"{crash_str} = crash to {mean_with:.0f}. "
                    f"Normal average: {mean_without:.1f}."
                ),
                icon=PATTERN_ICONS["crash"],
                data_summary=f"{len(with_scores)} crash days, avg {mean_with:.1f} vs {mean_without:.1f}",
            ))

    return patterns


def _detect_boost_patterns(
    days: List[DayRecord],
    metric: str,
) -> List[JournalPattern]:
    """Detect boost patterns: single factor with strong effect on a metric."""
    patterns = []
    all_factors = _collect_all_boolean_factors(days)

    for factor in all_factors:
        with_scores = [
            d.scores[metric] for d in days
            if d.factors.get(factor) is True and d.scores.get(metric) is not None
        ]
        without_scores = [
            d.scores[metric] for d in days
            if d.factors.get(factor) is not True and d.scores.get(metric) is not None
        ]

        if len(with_scores) < MIN_ENTRIES_FOR_PATTERNS or len(without_scores) < 3:
            continue

        mean_with = _mean(with_scores)
        mean_without = _mean(without_scores)

        # For negative factors, flip direction
        if factor in NEGATIVE_FACTORS:
            if mean_with >= mean_without:
                continue
            effect = _cohens_d(
                mean_without, mean_with,
                _std(without_scores), _std(with_scores),
                len(without_scores), len(with_scores),
            )
            direction = "negative"
        else:
            if mean_with <= mean_without:
                continue
            effect = _cohens_d(
                mean_with, mean_without,
                _std(with_scores), _std(without_scores),
                len(with_scores), len(without_scores),
            )
            direction = "positive"

        if effect < STRONG_EFFECT_SIZE:
            continue

        confidence = min(0.9, 0.4 + (len(with_scores) / 25) * 0.5)
        factor_label = factor.replace("_", " ").title()

        if direction == "positive":
            desc = (
                f"{factor_label} days average {mean_with:.1f} {metric} "
                f"vs {mean_without:.1f} without. Strong effect."
            )
        else:
            desc = (
                f"{factor_label} drops {metric} to {mean_with:.1f} "
                f"vs {mean_without:.1f} without. Significant impact."
            )

        patterns.append(JournalPattern(
            pattern_name=PATTERN_NAMES["boost"].format(factor=factor_label),
            pattern_type="boost",
            input_factors=[factor],
            output_metric=metric,
            mean_with=round(mean_with, 1),
            mean_without=round(mean_without, 1),
            effect_size=round(effect, 2),
            n_with=len(with_scores),
            n_without=len(without_scores),
            exceptions=0,
            confidence=round(confidence, 2),
            description=desc,
            icon=PATTERN_ICONS["boost"],
            data_summary=f"{len(with_scores)} days with, avg {mean_with:.1f} vs {mean_without:.1f}",
        ))

    return patterns


def _collect_all_boolean_factors(days: List[DayRecord]) -> List[str]:
    """Collect all unique boolean factors across all days."""
    factor_set: set = set()
    for d in days:
        for key, value in d.factors.items():
            if isinstance(value, bool) or value in (0, 1):
                factor_set.add(key)
    return sorted(factor_set)


# ── Main Entry Point ───────────────────────────────────────────────

def compute_journal_patterns(
    db: Session,
    user_id: int,
    window_days: int = 90,
) -> PatternComputeResponse:
    """
    Compute journal patterns from behavioral factors vs. scores.

    Runs all 4 detectors (floor, formula, crash, boost) across all score
    metrics, deduplicates, and feeds results into PatternManager.
    """
    from app.engine.memory.pattern_manager import PatternManager

    repo = DailyCheckInRepository(db)
    end_date = date.today()
    start_date = end_date - timedelta(days=window_days)

    checkins = repo.list_range(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=window_days,
    )

    # Build day records — only include days with behaviors_json
    # Separate V1 and V2 entries; pattern detection runs on the majority format
    days: List[DayRecord] = []
    for c in checkins:
        behaviors = c.behaviors_json or {}
        if not behaviors:
            continue
        bool_factors = _get_boolean_factors(behaviors)
        if not bool_factors:
            continue

        # V2 entries have overall_wellbeing set
        is_v2 = c.overall_wellbeing is not None
        if is_v2:
            scores = {
                "overall_wellbeing": c.overall_wellbeing,
                "energy": c.energy,
                "mood": c.mood,
                "focus": c.focus,
                "connection": c.connection,
            }
        else:
            scores = {
                "energy": c.energy,
                "mood": c.mood,
                "stress": c.stress,
                "focus": c.focus,
                "sleep_quality": c.sleep_quality,
            }
        days.append(DayRecord(
            checkin_date=c.checkin_date,
            factors=bool_factors,
            scores=scores,
        ))

    entries_count = len(days)
    minimum_met = entries_count >= MIN_ENTRIES_FOR_PATTERNS

    if not minimum_met:
        return PatternComputeResponse(
            patterns_found=0,
            patterns_updated=0,
            patterns_new=0,
            minimum_entries_met=False,
            entries_count=entries_count,
            entries_needed=MIN_ENTRIES_FOR_PATTERNS,
        )

    # Determine which metrics are present across all days
    # Use union of all score keys actually found in the data
    available_metrics = set()
    for d in days:
        available_metrics.update(k for k, v in d.scores.items() if v is not None)
    score_metrics = sorted(available_metrics) if available_metrics else SCORE_METRICS_V2

    # Run all detectors across all available metrics
    all_patterns: List[JournalPattern] = []
    for metric in score_metrics:
        all_patterns.extend(_detect_floor_patterns(days, metric))
        all_patterns.extend(_detect_formula_patterns(days, metric))
        all_patterns.extend(_detect_crash_patterns(days, metric))
        all_patterns.extend(_detect_boost_patterns(days, metric))

    # Deduplicate: keep highest-confidence pattern per (type, factors, metric)
    seen: Dict[str, JournalPattern] = {}
    for p in all_patterns:
        key = f"{p.pattern_type}:{','.join(sorted(p.input_factors))}:{p.output_metric}"
        if key not in seen or p.confidence > seen[key].confidence:
            seen[key] = p

    unique_patterns = list(seen.values())

    # Feed into PatternManager
    mgr = PatternManager(db)
    patterns_new = 0
    patterns_updated = 0

    for jp in unique_patterns:
        is_confirmed = jp.confidence >= 0.5 and jp.n_with >= MIN_ENTRIES_FOR_PATTERNS
        detection = mgr.detect_or_update_pattern(
            user_id=user_id,
            pattern_type=jp.pattern_type,
            input_signals=jp.input_factors,
            output_signal=jp.output_metric,
            confirmed=is_confirmed,
            relationship={
                "pattern_name": jp.pattern_name,
                "mean_with": jp.mean_with,
                "mean_without": jp.mean_without,
                "effect_size": jp.effect_size,
                "exceptions": jp.exceptions,
                "description": jp.description,
                "icon": jp.icon,
                "data_summary": jp.data_summary,
            },
        )
        if detection.action == "created":
            patterns_new += 1
        else:
            patterns_updated += 1

    logger.info(
        f"Journal patterns for user {user_id}: "
        f"{len(unique_patterns)} found, {patterns_new} new, {patterns_updated} updated"
    )

    return PatternComputeResponse(
        patterns_found=len(unique_patterns),
        patterns_updated=patterns_updated,
        patterns_new=patterns_new,
        minimum_entries_met=True,
        entries_count=entries_count,
        entries_needed=MIN_ENTRIES_FOR_PATTERNS,
    )
