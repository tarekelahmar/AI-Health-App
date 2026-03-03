"""Tests for Phase 3.3: Regime Detection."""

import pytest
from datetime import date, timedelta

from app.engine.memory.regime_classifier import (
    RegimeClassifier,
    Regime,
    RegimeClassification,
    RegimePeriod,
    REGIME_THRESHOLD,
)


@pytest.fixture
def classifier():
    return RegimeClassifier()


@pytest.fixture
def normal_baselines():
    """Typical healthy person baselines: (center, spread)."""
    return {
        "resting_hr": (62.0, 3.0),
        "hrv_rmssd": (45.0, 8.0),
        "sleep_duration": (420.0, 30.0),  # 7 hours
    }


class TestRegimeClassification:
    """Test regime classification from metric features."""

    def test_normal_regime_when_at_baseline(self, classifier, normal_baselines):
        """At-baseline values should classify as normal."""
        features = {
            "resting_hr": 62.0,
            "hrv_rmssd": 45.0,
            "sleep_duration": 420.0,
            "energy": 3.5,
            "stress": 2.0,
        }
        result = classifier.classify(features, normal_baselines)

        assert result.regime == Regime.NORMAL
        assert result.contributing_signals == []

    def test_illness_detection(self, classifier, normal_baselines):
        """Elevated RHR + suppressed HRV + low energy = illness."""
        features = {
            "resting_hr": 75.0,     # ~21% above baseline (62)
            "hrv_rmssd": 28.0,      # ~38% below baseline (45)
            "sleep_duration": 500.0, # ~19% above baseline (420)
            "energy": 1.5,          # Very low
        }
        result = classifier.classify(features, normal_baselines)

        assert result.regime == Regime.ILLNESS
        assert result.confidence >= REGIME_THRESHOLD
        assert "resting_hr" in result.contributing_signals
        assert "hrv_rmssd" in result.contributing_signals

    def test_high_stress_detection(self, classifier, normal_baselines):
        """High stress self-report + HRV suppression + elevated RHR."""
        features = {
            "resting_hr": 70.0,     # ~13% above
            "hrv_rmssd": 33.0,      # ~27% below
            "sleep_duration": 340.0, # ~19% below
            "stress": 4.5,          # High stress
        }
        result = classifier.classify(features, normal_baselines)

        assert result.regime == Regime.HIGH_STRESS
        assert result.confidence >= REGIME_THRESHOLD

    def test_recovery_detection(self, classifier, normal_baselines):
        """Rising HRV + lower RHR + more sleep = recovery."""
        features = {
            "resting_hr": 58.0,     # ~6.5% below baseline
            "hrv_rmssd": 52.0,      # ~16% above baseline
            "sleep_duration": 480.0, # ~14% above baseline
            "energy": 4.0,          # Good energy
        }
        result = classifier.classify(features, normal_baselines)

        assert result.regime == Regime.RECOVERY
        assert result.confidence >= REGIME_THRESHOLD

    def test_no_regime_detected_with_missing_data(self, classifier, normal_baselines):
        """With no features, should classify as normal."""
        features = {}
        result = classifier.classify(features, normal_baselines)

        assert result.regime == Regime.NORMAL

    def test_partial_data_still_classifies(self, classifier, normal_baselines):
        """Should work with partial metric coverage."""
        features = {
            "resting_hr": 75.0,
            "energy": 1.5,
        }
        result = classifier.classify(features, normal_baselines)

        # May or may not trigger illness — depends on weights
        # At minimum, should not crash
        assert result.regime in list(Regime)

    def test_confidence_bounded(self, classifier, normal_baselines):
        """Confidence should be between 0 and 1."""
        features = {
            "resting_hr": 90.0,
            "hrv_rmssd": 15.0,
            "sleep_duration": 600.0,
            "energy": 1.0,
        }
        result = classifier.classify(features, normal_baselines)

        assert 0.0 <= result.confidence <= 1.0


class TestRegimeSuppression:
    """Test insight suppression during certain regimes."""

    def test_illness_suppresses(self, classifier):
        assert classifier.should_suppress_insights(Regime.ILLNESS) is True

    def test_travel_suppresses(self, classifier):
        assert classifier.should_suppress_insights(Regime.TRAVEL) is True

    def test_normal_does_not_suppress(self, classifier):
        assert classifier.should_suppress_insights(Regime.NORMAL) is False

    def test_stress_does_not_suppress(self, classifier):
        assert classifier.should_suppress_insights(Regime.HIGH_STRESS) is False


class TestRegimeContext:
    """Test human-readable regime context."""

    def test_all_regimes_have_context(self, classifier):
        for regime in Regime:
            context = classifier.get_regime_context(regime)
            assert isinstance(context, str)
            assert len(context) > 0


class TestRegimeTimeline:
    """Test building regime timeline from daily classifications."""

    def test_single_regime_period(self, classifier):
        classifications = [
            RegimeClassification(
                regime=Regime.NORMAL,
                confidence=0.8,
                contributing_signals=[],
                date=date(2026, 1, d),
            )
            for d in range(1, 6)
        ]

        periods = classifier.build_regime_timeline(classifications)
        assert len(periods) == 1
        assert periods[0].regime == Regime.NORMAL
        assert periods[0].start_date == date(2026, 1, 1)
        assert periods[0].end_date == date(2026, 1, 5)

    def test_multiple_regime_periods(self, classifier):
        classifications = [
            # Normal for 3 days
            RegimeClassification(Regime.NORMAL, 0.8, [], date(2026, 1, 1)),
            RegimeClassification(Regime.NORMAL, 0.8, [], date(2026, 1, 2)),
            RegimeClassification(Regime.NORMAL, 0.8, [], date(2026, 1, 3)),
            # Illness for 4 days
            RegimeClassification(Regime.ILLNESS, 0.7, ["resting_hr"], date(2026, 1, 4)),
            RegimeClassification(Regime.ILLNESS, 0.8, ["resting_hr"], date(2026, 1, 5)),
            RegimeClassification(Regime.ILLNESS, 0.6, ["resting_hr"], date(2026, 1, 6)),
            RegimeClassification(Regime.ILLNESS, 0.5, ["resting_hr"], date(2026, 1, 7)),
            # Recovery for 2 days
            RegimeClassification(Regime.RECOVERY, 0.6, ["hrv_rmssd"], date(2026, 1, 8)),
            RegimeClassification(Regime.RECOVERY, 0.7, ["hrv_rmssd"], date(2026, 1, 9)),
        ]

        periods = classifier.build_regime_timeline(classifications)

        assert len(periods) == 3
        assert periods[0].regime == Regime.NORMAL
        assert periods[1].regime == Regime.ILLNESS
        assert periods[2].regime == Regime.RECOVERY

        # Check illness period dates
        assert periods[1].start_date == date(2026, 1, 4)
        assert periods[1].end_date == date(2026, 1, 7)

        # Check average confidence
        assert periods[1].avg_confidence == pytest.approx(
            (0.7 + 0.8 + 0.6 + 0.5) / 4, abs=0.01
        )

    def test_empty_timeline(self, classifier):
        periods = classifier.build_regime_timeline([])
        assert periods == []

    def test_unsorted_input_handled(self, classifier):
        """Should sort by date before building periods."""
        classifications = [
            RegimeClassification(Regime.ILLNESS, 0.7, [], date(2026, 1, 3)),
            RegimeClassification(Regime.NORMAL, 0.8, [], date(2026, 1, 1)),
            RegimeClassification(Regime.NORMAL, 0.8, [], date(2026, 1, 2)),
        ]

        periods = classifier.build_regime_timeline(classifications)
        assert len(periods) == 2
        assert periods[0].regime == Regime.NORMAL
        assert periods[0].start_date == date(2026, 1, 1)
        assert periods[1].regime == Regime.ILLNESS
