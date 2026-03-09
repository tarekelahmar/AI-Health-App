"""Tests for Phase 5.2: Risk Window Detection."""

import pytest
from app.engine.forecasting.risk_detector import (
    RiskWindowDetector,
    RiskLevel,
    RiskAssessment,
    ContributingFactor,
    RISK_DEFINITIONS,
    RISK_THRESHOLDS,
    RISK_ACTIONS,
)


# ── Helpers ─────────────────────────────────────────────────────────


def _normal_baselines():
    """Baselines representing a healthy individual."""
    return {
        "hrv_rmssd_ms": (55.0, 12.0),
        "resting_heart_rate_bpm": (58.0, 4.0),
        "sleep_duration_minutes": (450.0, 30.0),
        "sleep_efficiency_pct": (0.88, 0.04),
        "respiratory_rate_brpm": (14.5, 1.0),
        "subjective_energy": (3.5, 0.8),
        "subjective_stress": (2.0, 0.7),
    }


def _normal_values():
    """Recent values near baseline (healthy)."""
    return {
        "hrv_rmssd_ms": 54.0,
        "resting_heart_rate_bpm": 59.0,
        "sleep_duration_minutes": 445.0,
        "sleep_efficiency_pct": 0.87,
        "respiratory_rate_brpm": 14.6,
        "subjective_energy": 3.4,
        "subjective_stress": 2.1,
    }


def _illness_vulnerable_values():
    """Values indicating immune suppression."""
    return {
        "hrv_rmssd_ms": 25.0,         # Way below baseline
        "resting_heart_rate_bpm": 72.0, # Elevated
        "sleep_duration_minutes": 360.0, # Short sleep
        "sleep_efficiency_pct": 0.72,    # Poor efficiency
        "respiratory_rate_brpm": 17.5,   # Elevated
        "subjective_energy": 1.5,
        "subjective_stress": 4.0,
    }


def _burnout_values():
    """Values indicating burnout trajectory."""
    return {
        "hrv_rmssd_ms": 35.0,
        "resting_heart_rate_bpm": 66.0,
        "sleep_duration_minutes": 400.0,
        "sleep_efficiency_pct": 0.78,
        "respiratory_rate_brpm": 15.0,
        "subjective_energy": 1.5,        # Very low energy
        "subjective_stress": 4.5,         # Very high stress
    }


# ── Test Risk Detector ─────────────────────────────────────────────


class TestRiskDetector:
    """Test core risk detection logic."""

    @pytest.fixture
    def detector(self):
        return RiskWindowDetector()

    def test_normal_values_low_risk(self, detector):
        """Healthy values should produce low risk across all types."""
        for risk_type in RISK_DEFINITIONS:
            result = detector.detect(
                risk_type, _normal_values(), _normal_baselines()
            )
            assert result.risk_level == RiskLevel.LOW
            assert result.risk_score < 0.3

    def test_illness_vulnerability_detected(self, detector):
        """Should detect elevated illness vulnerability."""
        result = detector.detect(
            "illness_vulnerability",
            _illness_vulnerable_values(),
            _normal_baselines(),
        )
        assert result.risk_level in (RiskLevel.ELEVATED, RiskLevel.HIGH)
        assert result.risk_score > 0.5

    def test_burnout_detected(self, detector):
        """Should detect burnout trajectory."""
        result = detector.detect(
            "burnout_trajectory",
            _burnout_values(),
            _normal_baselines(),
        )
        assert result.risk_level in (RiskLevel.MODERATE, RiskLevel.ELEVATED, RiskLevel.HIGH)
        assert result.risk_score > 0.3

    def test_contributing_factors_present(self, detector):
        """Should list contributing factors with deviations."""
        result = detector.detect(
            "illness_vulnerability",
            _illness_vulnerable_values(),
            _normal_baselines(),
        )
        assert len(result.contributing_factors) > 0
        for factor in result.contributing_factors:
            assert factor.metric != ""
            assert factor.weight > 0

    def test_factors_sorted_by_deviation(self, detector):
        """Contributing factors should be sorted by deviation magnitude."""
        result = detector.detect(
            "illness_vulnerability",
            _illness_vulnerable_values(),
            _normal_baselines(),
        )
        deviations = [abs(f.deviation_pct) for f in result.contributing_factors]
        assert deviations == sorted(deviations, reverse=True)

    def test_unknown_risk_type_raises(self, detector):
        with pytest.raises(ValueError, match="Unknown risk type"):
            detector.detect("unknown_type", {}, {})

    def test_missing_metrics_handled(self, detector):
        """Should work with partial metric availability."""
        result = detector.detect(
            "illness_vulnerability",
            {"hrv_rmssd_ms": 25.0},  # Only one metric
            {"hrv_rmssd_ms": (55.0, 12.0)},
        )
        assert result is not None
        assert len(result.contributing_factors) == 1

    def test_no_data_returns_low_risk(self, detector):
        """No matching metrics should return low risk."""
        result = detector.detect(
            "illness_vulnerability",
            {"unrelated_metric": 42.0},
            {"unrelated_metric": (40.0, 5.0)},
        )
        assert result.risk_level == RiskLevel.LOW
        assert result.risk_score == 0.0


# ── Test Risk Levels ───────────────────────────────────────────────


class TestRiskLevels:

    def test_threshold_ordering(self):
        """Thresholds should be ordered LOW < MODERATE < ELEVATED < HIGH."""
        assert RISK_THRESHOLDS[RiskLevel.LOW] < RISK_THRESHOLDS[RiskLevel.MODERATE]
        assert RISK_THRESHOLDS[RiskLevel.MODERATE] < RISK_THRESHOLDS[RiskLevel.ELEVATED]
        assert RISK_THRESHOLDS[RiskLevel.ELEVATED] < RISK_THRESHOLDS[RiskLevel.HIGH]

    def test_all_risk_types_have_actions(self):
        """All risk types should have recommended actions."""
        for risk_type in RISK_DEFINITIONS:
            assert risk_type in RISK_ACTIONS
            actions = RISK_ACTIONS[risk_type]
            assert "moderate" in actions
            assert "elevated" in actions
            assert "high" in actions

    def test_low_risk_no_actions(self):
        detector = RiskWindowDetector()
        result = detector.detect(
            "illness_vulnerability",
            _normal_values(),
            _normal_baselines(),
        )
        assert result.recommended_actions == []


# ── Test Detect All ────────────────────────────────────────────────


class TestDetectAll:

    def test_returns_all_risk_types(self):
        detector = RiskWindowDetector()
        results = detector.detect_all(_normal_values(), _normal_baselines())
        assert len(results) == len(RISK_DEFINITIONS)

    def test_sorted_by_risk_score(self):
        detector = RiskWindowDetector()
        results = detector.detect_all(
            _illness_vulnerable_values(), _normal_baselines()
        )
        scores = [r.risk_score for r in results]
        assert scores == sorted(scores, reverse=True)


# ── Test Risk Descriptions ─────────────────────────────────────────


class TestRiskDescriptions:

    def test_low_risk_description(self):
        detector = RiskWindowDetector()
        result = detector.detect(
            "sleep_debt", _normal_values(), _normal_baselines()
        )
        assert "low" in result.description.lower()

    def test_elevated_risk_has_factors_in_description(self):
        detector = RiskWindowDetector()
        result = detector.detect(
            "illness_vulnerability",
            _illness_vulnerable_values(),
            _normal_baselines(),
        )
        if result.risk_level != RiskLevel.LOW:
            assert "baseline" in result.description.lower()


# ── Test Trend Risk ────────────────────────────────────────────────


class TestTrendRisk:

    def test_worsening_trend_increases_risk(self):
        """A consistently worsening trend should increase risk score."""
        detector = RiskWindowDetector()

        # Without trend history
        values_no_trend = {
            "hrv_rmssd_ms": 40.0,
            "resting_heart_rate_bpm": 64.0,
            "sleep_duration_minutes": 400.0,
            "sleep_efficiency_pct": 0.80,
            "respiratory_rate_brpm": 15.5,
        }
        result_no_trend = detector.detect(
            "illness_vulnerability",
            values_no_trend,
            _normal_baselines(),
        )

        # With worsening trend history
        declining_hrv = [55.0, 50.0, 45.0, 42.0, 40.0]
        rising_rhr = [58.0, 60.0, 62.0, 63.0, 64.0]
        result_with_trend = detector.detect(
            "illness_vulnerability",
            values_no_trend,
            _normal_baselines(),
            days_history={
                "hrv_rmssd_ms": declining_hrv,
                "resting_heart_rate_bpm": rising_rhr,
            },
        )

        assert result_with_trend.risk_score >= result_no_trend.risk_score


# ── Test Risk Configuration ────────────────────────────────────────


class TestRiskConfiguration:

    def test_all_risk_types_weights_sum_to_one(self):
        """Weights for each risk type should sum to 1.0."""
        for risk_type, signals in RISK_DEFINITIONS.items():
            total = sum(s["weight"] for s in signals)
            assert abs(total - 1.0) < 0.01, f"{risk_type} weights sum to {total}"

    def test_all_directions_valid(self):
        for risk_type, signals in RISK_DEFINITIONS.items():
            for s in signals:
                assert s["direction"] in ("above", "below"), (
                    f"Invalid direction '{s['direction']}' in {risk_type}"
                )
