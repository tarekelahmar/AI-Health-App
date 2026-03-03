"""
Tests for the Journal Pattern Engine — deterministic pattern detection.

Tests all 4 pattern types: floor, formula, crash, boost.
Also tests minimum data requirements and edge cases.
"""

import pytest
from datetime import date, timedelta

from app.engine.journal_pattern_engine import (
    DayRecord,
    _detect_floor_patterns,
    _detect_formula_patterns,
    _detect_crash_patterns,
    _detect_boost_patterns,
    _cohens_d,
    _std,
    _mean,
    _get_boolean_factors,
    _collect_all_boolean_factors,
    MIN_ENTRIES_FOR_PATTERNS,
    FLOOR_THRESHOLD,
)


# ── Helpers ───────────────────────────────────────────────────────

def _make_day(
    day_offset: int,
    factors: dict,
    energy: float = 5.0,
    mood: float = 5.0,
    stress: float = 5.0,
    focus: float = 5.0,
    sleep_quality: float = 5.0,
) -> DayRecord:
    """Create a DayRecord for testing."""
    return DayRecord(
        checkin_date=date.today() - timedelta(days=day_offset),
        factors=factors,
        scores={
            "energy": energy,
            "mood": mood,
            "stress": stress,
            "focus": focus,
            "sleep_quality": sleep_quality,
        },
    )


# ── Statistics Helper Tests ───────────────────────────────────────

class TestStatisticsHelpers:
    def test_mean_empty(self):
        assert _mean([]) == 0.0

    def test_mean_values(self):
        assert _mean([2.0, 4.0, 6.0]) == 4.0

    def test_std_single_value(self):
        assert _std([5.0]) == 0.0

    def test_std_values(self):
        result = _std([2.0, 4.0, 6.0])
        assert abs(result - 2.0) < 0.01

    def test_cohens_d_identical(self):
        result = _cohens_d(5.0, 5.0, 1.0, 1.0, 10, 10)
        assert result == 0.0

    def test_cohens_d_large_effect(self):
        result = _cohens_d(8.0, 4.0, 1.0, 1.0, 10, 10)
        assert result > 2.0  # Very large effect

    def test_cohens_d_insufficient_data(self):
        result = _cohens_d(8.0, 4.0, 1.0, 1.0, 1, 1)
        assert result == 0.0

    def test_get_boolean_factors(self):
        factors = {"exercised": True, "alcohol": False, "exercise_minutes": 30, "notes": "good"}
        result = _get_boolean_factors(factors)
        assert result == {"exercised": True, "alcohol": False}

    def test_get_boolean_factors_with_int_booleans(self):
        factors = {"exercised": 1, "alcohol": 0}
        result = _get_boolean_factors(factors)
        assert result == {"exercised": True, "alcohol": False}


# ── Floor Pattern Tests ───────────────────────────────────────────

class TestFloorPatterns:
    def test_floor_detected_when_factor_guarantees_minimum(self):
        """Exercise days all score >= 6, non-exercise days much lower."""
        days = []
        # 10 exercise days with high energy
        for i in range(10):
            days.append(_make_day(i, {"exercised": True}, energy=8.0))
        # 10 non-exercise days with low energy
        for i in range(10, 20):
            days.append(_make_day(i, {"exercised": False}, energy=3.0))

        patterns = _detect_floor_patterns(days, "energy")
        assert len(patterns) >= 1
        floor = patterns[0]
        assert floor.pattern_type == "floor"
        assert "exercised" in floor.input_factors
        assert floor.mean_with > floor.mean_without
        assert "Floor" in floor.pattern_name

    def test_floor_not_detected_when_exceptions(self):
        """Too many exceptions (scores below threshold) prevent floor detection."""
        days = []
        # Exercise days with some low scores
        for i in range(5):
            days.append(_make_day(i, {"exercised": True}, energy=8.0))
        for i in range(5, 10):
            days.append(_make_day(i, {"exercised": True}, energy=3.0))  # Below threshold
        for i in range(10, 20):
            days.append(_make_day(i, {"exercised": False}, energy=3.0))

        patterns = _detect_floor_patterns(days, "energy")
        # Should NOT detect floor since 5 exceptions out of 10
        assert len(patterns) == 0

    def test_floor_not_detected_with_insufficient_data(self):
        """Fewer than MIN_ENTRIES_FOR_PATTERNS should not detect patterns."""
        days = []
        for i in range(3):
            days.append(_make_day(i, {"exercised": True}, energy=9.0))
        for i in range(3, 6):
            days.append(_make_day(i, {"exercised": False}, energy=3.0))

        patterns = _detect_floor_patterns(days, "energy")
        assert len(patterns) == 0

    def test_floor_not_detected_when_no_effect(self):
        """No floor when scores are similar with and without factor."""
        days = []
        for i in range(10):
            days.append(_make_day(i, {"exercised": True}, energy=7.0))
        for i in range(10, 20):
            days.append(_make_day(i, {"exercised": False}, energy=7.0))

        patterns = _detect_floor_patterns(days, "energy")
        assert len(patterns) == 0


# ── Formula Pattern Tests ─────────────────────────────────────────

class TestFormulaPatterns:
    def test_formula_detected_for_positive_combination(self):
        """Combination of exercised + social_contact predicts high scores."""
        days = []
        # 10 combo days with very high energy
        for i in range(10):
            days.append(_make_day(i, {"exercised": True, "social_contact": True}, energy=9.0))
        # 10 days with neither — low energy
        for i in range(10, 20):
            days.append(_make_day(i, {"exercised": False, "social_contact": False}, energy=3.0))

        patterns = _detect_formula_patterns(days, "energy")
        assert len(patterns) >= 1
        formula = patterns[0]
        assert formula.pattern_type == "formula"
        assert set(formula.input_factors) == {"exercised", "social_contact"}
        assert formula.mean_with >= 7

    def test_formula_not_detected_when_combo_score_is_low(self):
        """No formula pattern when combo days don't hit HIGH_SCORE_THRESHOLD."""
        days = []
        for i in range(10):
            days.append(_make_day(i, {"exercised": True, "social_contact": True}, energy=5.0))
        for i in range(10, 20):
            days.append(_make_day(i, {"exercised": False, "social_contact": False}, energy=4.0))

        patterns = _detect_formula_patterns(days, "energy")
        assert len(patterns) == 0

    def test_formula_excludes_negative_factors(self):
        """Negative factors (alcohol, etc.) should not appear in formula combos."""
        days = []
        for i in range(10):
            days.append(_make_day(i, {"alcohol": True, "caffeine_late": True}, energy=8.0))
        for i in range(10, 20):
            days.append(_make_day(i, {"alcohol": False, "caffeine_late": False}, energy=4.0))

        patterns = _detect_formula_patterns(days, "energy")
        # alcohol and caffeine_late are NEGATIVE_FACTORS, should not form formula
        assert len(patterns) == 0


# ── Crash Pattern Tests ───────────────────────────────────────────

class TestCrashPatterns:
    def test_crash_detected_for_negative_combo(self):
        """Isolation + no exercise → crash to low scores."""
        days = []
        # 10 crash days: isolated=True AND exercised=False
        for i in range(10):
            days.append(_make_day(
                i,
                {"isolated": True, "exercised": False},
                energy=2.0,
            ))
        # 10 normal days
        for i in range(10, 20):
            days.append(_make_day(
                i,
                {"isolated": False, "exercised": True},
                energy=7.0,
            ))

        patterns = _detect_crash_patterns(days, "energy")
        assert len(patterns) >= 1
        crash = patterns[0]
        assert crash.pattern_type == "crash"
        assert crash.mean_with <= 4

    def test_crash_not_detected_when_scores_not_low(self):
        """No crash if scores with negative combo are still acceptable."""
        days = []
        for i in range(10):
            days.append(_make_day(i, {"isolated": True, "exercised": False}, energy=6.0))
        for i in range(10, 20):
            days.append(_make_day(i, {"isolated": False, "exercised": True}, energy=7.0))

        patterns = _detect_crash_patterns(days, "energy")
        assert len(patterns) == 0


# ── Boost Pattern Tests ───────────────────────────────────────────

class TestBoostPatterns:
    def test_boost_detected_for_strong_single_factor(self):
        """Meditation has a strong positive effect on mood."""
        days = []
        for i in range(10):
            days.append(_make_day(i, {"meditation": True}, mood=9.0))
        for i in range(10, 20):
            days.append(_make_day(i, {"meditation": False}, mood=4.0))

        patterns = _detect_boost_patterns(days, "mood")
        assert len(patterns) >= 1
        boost = patterns[0]
        assert boost.pattern_type == "boost"
        assert "meditation" in boost.input_factors
        assert boost.effect_size >= 0.8
        assert "Boost" in boost.pattern_name

    def test_boost_not_detected_for_weak_effect(self):
        """No boost when effect size is too small (high variance, small difference)."""
        import random
        random.seed(99)
        days = []
        # With meditation: scores around 5.5 but with high variance
        for i in range(10):
            days.append(_make_day(i, {"meditation": True}, mood=5.0 + random.uniform(-2, 2.5)))
        # Without meditation: scores around 5.0 with high variance
        for i in range(10, 20):
            days.append(_make_day(i, {"meditation": False}, mood=5.0 + random.uniform(-2, 2)))

        patterns = _detect_boost_patterns(days, "mood")
        assert len(patterns) == 0

    def test_boost_detects_negative_factor_impact(self):
        """Late caffeine has a strong negative effect on sleep quality."""
        days = []
        for i in range(10):
            days.append(_make_day(i, {"caffeine_late": True}, sleep_quality=3.0))
        for i in range(10, 20):
            days.append(_make_day(i, {"caffeine_late": False}, sleep_quality=8.0))

        patterns = _detect_boost_patterns(days, "sleep_quality")
        assert len(patterns) >= 1
        boost = patterns[0]
        assert "caffeine_late" in boost.input_factors


# ── Collect Boolean Factors Tests ─────────────────────────────────

class TestCollectBooleanFactors:
    def test_collects_unique_boolean_factors(self):
        days = [
            _make_day(0, {"exercised": True, "alcohol": False}),
            _make_day(1, {"exercised": False, "meditation": True}),
            _make_day(2, {"exercised": True, "meditation": False, "outdoors": True}),
        ]
        factors = _collect_all_boolean_factors(days)
        assert sorted(factors) == ["alcohol", "exercised", "meditation", "outdoors"]

    def test_ignores_non_boolean_factors(self):
        days = [
            _make_day(0, {"exercised": True, "exercise_minutes": 30, "notes": "good"}),
        ]
        factors = _collect_all_boolean_factors(days)
        assert factors == ["exercised"]


# ── No Spurious Patterns Tests ────────────────────────────────────

class TestNoSpuriousPatterns:
    def test_no_patterns_from_random_data(self):
        """All scores hovering around 5 with random factors should not produce patterns."""
        import random
        random.seed(42)
        days = []
        factor_keys = ["exercised", "meditation", "social_contact", "alcohol"]
        for i in range(30):
            factors = {k: random.choice([True, False]) for k in factor_keys}
            days.append(_make_day(
                i, factors,
                energy=5 + random.uniform(-0.5, 0.5),
                mood=5 + random.uniform(-0.5, 0.5),
            ))

        # With small variance around 5, no strong patterns should emerge
        floor = _detect_floor_patterns(days, "energy")
        boost = _detect_boost_patterns(days, "energy")
        assert len(floor) == 0
        assert len(boost) == 0
