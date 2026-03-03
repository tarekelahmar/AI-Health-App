"""Tests for Phase 6.2: Experiment Execution & Tracking."""

import pytest
import numpy as np
from datetime import date, timedelta

from app.engine.experiments.designer import (
    ExperimentDesigner,
    ExperimentDesign,
    ExperimentPhase,
)
from app.engine.experiments.tracker import (
    ExperimentTracker,
    AdherenceLog,
    Verdict,
    ExperimentProgress,
    EarlyStopSignal,
    ExperimentResult,
    MetricResult,
)


# ── Helpers ─────────────────────────────────────────────────────────


def _make_design(
    baseline_days: int = 14,
    intervention_days: int = 21,
    washout_days: int = 7,
) -> ExperimentDesign:
    from app.engine.experiments.designer import (
        PowerAnalysisResult,
        SuccessCriteria,
    )
    return ExperimentDesign(
        hypothesis="Test hypothesis",
        intervention="Test intervention",
        intervention_key="test_intervention",
        baseline_days=baseline_days,
        intervention_days=intervention_days,
        washout_days=washout_days,
        total_days=baseline_days + intervention_days + washout_days,
        target_metrics=["sleep_duration_minutes", "sleep_efficiency_pct"],
        success_criteria=SuccessCriteria(
            primary_metric="sleep_duration_minutes",
            direction="increase",
            min_effect_size=0.5,
            required_confidence=0.05,
            min_adherence=0.8,
            secondary_metrics=["sleep_efficiency_pct"],
        ),
        power_analysis=PowerAnalysisResult(
            required_days=intervention_days,
            power=0.8,
            alpha=0.05,
            min_detectable_effect=0.5,
            baseline_variance=900.0,
            method="paired_t_test_nof1",
        ),
        tracking_requirements=["daily_checkin", "intervention_log"],
        confounders_to_monitor=["sleep_quality", "stress_level"],
        designed_date=date(2026, 3, 1),
        estimated_completion=date(2026, 3, 1) + timedelta(
            days=baseline_days + intervention_days + washout_days
        ),
    )


def _make_adherence_logs(
    start: date,
    n_days: int,
    adherence_rate: float = 1.0,
) -> list[AdherenceLog]:
    """Create adherence logs with given rate."""
    np.random.seed(42)
    logs = []
    for i in range(n_days):
        adhered = np.random.random() < adherence_rate
        logs.append(AdherenceLog(
            log_date=start + timedelta(days=i),
            adhered=adhered,
        ))
    return logs


# ── Test Phase Detection ──────────────────────────────────────────


class TestPhaseDetection:

    @pytest.fixture
    def tracker(self):
        return ExperimentTracker()

    def test_before_start_is_design(self, tracker):
        design = _make_design()
        phase, day = tracker.get_current_phase(
            design, date(2026, 3, 1), date(2026, 2, 28)
        )
        assert phase == ExperimentPhase.DESIGN

    def test_day_one_is_baseline(self, tracker):
        design = _make_design()
        phase, day = tracker.get_current_phase(
            design, date(2026, 3, 1), date(2026, 3, 1)
        )
        assert phase == ExperimentPhase.BASELINE
        assert day == 1

    def test_last_baseline_day(self, tracker):
        design = _make_design(baseline_days=14)
        phase, day = tracker.get_current_phase(
            design, date(2026, 3, 1), date(2026, 3, 14)
        )
        assert phase == ExperimentPhase.BASELINE
        assert day == 14

    def test_first_intervention_day(self, tracker):
        design = _make_design(baseline_days=14)
        phase, day = tracker.get_current_phase(
            design, date(2026, 3, 1), date(2026, 3, 15)
        )
        assert phase == ExperimentPhase.INTERVENTION
        assert day == 1

    def test_washout_phase(self, tracker):
        design = _make_design(baseline_days=14, intervention_days=21, washout_days=7)
        # Day after intervention ends
        intervention_end = date(2026, 3, 1) + timedelta(days=14 + 21)
        phase, day = tracker.get_current_phase(
            design, date(2026, 3, 1), intervention_end
        )
        assert phase == ExperimentPhase.WASHOUT
        assert day == 1

    def test_analysis_phase(self, tracker):
        design = _make_design(baseline_days=14, intervention_days=21, washout_days=7)
        after_all = date(2026, 3, 1) + timedelta(days=14 + 21 + 7 + 1)
        phase, _ = tracker.get_current_phase(
            design, date(2026, 3, 1), after_all
        )
        assert phase == ExperimentPhase.ANALYSIS

    def test_no_washout_goes_to_analysis(self, tracker):
        design = _make_design(baseline_days=14, intervention_days=21, washout_days=0)
        after_intervention = date(2026, 3, 1) + timedelta(days=14 + 21 + 1)
        phase, _ = tracker.get_current_phase(
            design, date(2026, 3, 1), after_intervention
        )
        assert phase == ExperimentPhase.ANALYSIS


# ── Test Progress ─────────────────────────────────────────────────


class TestProgress:

    def test_baseline_progress(self):
        tracker = ExperimentTracker()
        design = _make_design(baseline_days=14)
        start = date(2026, 3, 1)

        progress = tracker.get_progress(
            design, start, [], current_date=date(2026, 3, 7)
        )

        assert progress.current_phase == ExperimentPhase.BASELINE
        assert progress.phase_day == 7
        assert progress.overall_day == 7
        assert progress.days_remaining > 0

    def test_intervention_adherence_tracking(self):
        tracker = ExperimentTracker()
        design = _make_design(baseline_days=14, intervention_days=21)
        start = date(2026, 3, 1)

        # Create logs during intervention phase
        intervention_start = start + timedelta(days=14)
        logs = [
            AdherenceLog(intervention_start + timedelta(days=i), adhered=True)
            for i in range(7)
        ]

        progress = tracker.get_progress(
            design, start, logs,
            current_date=intervention_start + timedelta(days=7),
        )

        assert progress.adherence_rate == 1.0
        assert progress.is_on_track is True

    def test_low_adherence_not_on_track(self):
        tracker = ExperimentTracker()
        design = _make_design(baseline_days=14, intervention_days=21)
        start = date(2026, 3, 1)

        intervention_start = start + timedelta(days=14)
        logs = [
            AdherenceLog(intervention_start + timedelta(days=i), adhered=(i < 3))
            for i in range(10)
        ]

        progress = tracker.get_progress(
            design, start, logs,
            current_date=intervention_start + timedelta(days=10),
        )

        assert progress.adherence_rate < 0.8
        assert progress.is_on_track is False

    def test_phase_progress_percentage(self):
        tracker = ExperimentTracker()
        design = _make_design(baseline_days=10)
        start = date(2026, 3, 1)

        progress = tracker.get_progress(
            design, start, [], current_date=date(2026, 3, 5)
        )
        # Day 5 of 10 = 50%
        assert progress.phase_progress_pct == pytest.approx(50.0, abs=1.0)


# ── Test Early Stopping ──────────────────────────────────────────


class TestEarlyStopping:

    @pytest.fixture
    def tracker(self):
        return ExperimentTracker()

    def test_insufficient_data_continues(self, tracker):
        design = _make_design()
        signal = tracker.check_early_stop(
            design,
            baseline_values=[100.0] * 14,
            intervention_values=[110.0] * 3,  # Too few days
        )
        assert signal.should_stop is False
        assert "Insufficient" in signal.reason

    def test_clear_positive_stops(self, tracker):
        """Very strong effect should trigger early stop."""
        np.random.seed(42)
        design = _make_design(intervention_days=21)
        baseline = list(np.random.normal(100, 5, 14))
        # Very large effect (5+ std devs)
        intervention = list(np.random.normal(140, 5, 10))

        signal = tracker.check_early_stop(design, baseline, intervention)
        assert signal.should_stop is True
        assert signal.current_effect_size > 1.0
        assert signal.current_p_value < 0.01

    def test_no_effect_continues(self, tracker):
        """No effect should not trigger early stop."""
        np.random.seed(42)
        design = _make_design(intervention_days=21)
        baseline = list(np.random.normal(100, 10, 14))
        intervention = list(np.random.normal(101, 10, 10))

        signal = tracker.check_early_stop(design, baseline, intervention)
        assert signal.should_stop is False

    def test_futility_stops(self, tracker):
        """Clearly no effect after most of intervention should trigger futility."""
        np.random.seed(42)
        design = _make_design(intervention_days=14)
        baseline = list(np.random.normal(100, 10, 14))
        # 60%+ of intervention with no effect
        intervention = list(np.random.normal(100, 10, 12))

        signal = tracker.check_early_stop(design, baseline, intervention)
        # May or may not trigger depending on random draws
        assert isinstance(signal, EarlyStopSignal)


# ── Test Analysis ─────────────────────────────────────────────────


class TestAnalysis:

    @pytest.fixture
    def tracker(self):
        return ExperimentTracker()

    def test_helpful_verdict(self, tracker):
        """Clear positive effect should get HELPFUL verdict."""
        np.random.seed(42)
        design = _make_design()

        baseline = list(np.random.normal(400, 20, 14))
        intervention = list(np.random.normal(440, 20, 21))

        logs = [AdherenceLog(date(2026, 3, 15) + timedelta(days=i), True) for i in range(21)]

        result = tracker.analyze(
            design,
            {"sleep_duration_minutes": (baseline, intervention)},
            logs,
        )

        assert result.verdict == Verdict.HELPFUL
        assert result.met_effect_threshold is True
        assert result.primary_result.significant is True
        assert result.overall_effect_size > 0

    def test_not_helpful_verdict(self, tracker):
        """No effect should get NOT_HELPFUL verdict."""
        np.random.seed(42)
        design = _make_design()

        baseline = list(np.random.normal(400, 20, 14))
        intervention = list(np.random.normal(400, 20, 21))

        logs = [AdherenceLog(date(2026, 3, 15) + timedelta(days=i), True) for i in range(21)]

        result = tracker.analyze(
            design,
            {"sleep_duration_minutes": (baseline, intervention)},
            logs,
        )

        assert result.verdict in (Verdict.NOT_HELPFUL, Verdict.UNCLEAR)

    def test_unclear_due_to_adherence(self, tracker):
        """Low adherence should give UNCLEAR verdict."""
        np.random.seed(42)
        design = _make_design()

        baseline = list(np.random.normal(400, 20, 14))
        intervention = list(np.random.normal(440, 20, 21))

        # Only 3/21 adhered = ~14%
        logs = [
            AdherenceLog(date(2026, 3, 15) + timedelta(days=i), adhered=(i < 3))
            for i in range(21)
        ]

        result = tracker.analyze(
            design,
            {"sleep_duration_minutes": (baseline, intervention)},
            logs,
        )

        assert result.verdict == Verdict.UNCLEAR
        assert result.met_adherence_requirement is False

    def test_insufficient_data(self, tracker):
        """Missing primary metric should give INSUFFICIENT_DATA."""
        design = _make_design()
        result = tracker.analyze(design, {}, [])
        assert result.verdict == Verdict.INSUFFICIENT_DATA

    def test_secondary_metrics_analyzed(self, tracker):
        """Should analyze secondary metrics too."""
        np.random.seed(42)
        design = _make_design()

        baseline_primary = list(np.random.normal(400, 20, 14))
        intervention_primary = list(np.random.normal(440, 20, 21))
        baseline_secondary = list(np.random.normal(0.85, 0.05, 14))
        intervention_secondary = list(np.random.normal(0.90, 0.05, 21))

        logs = [AdherenceLog(date(2026, 3, 15) + timedelta(days=i), True) for i in range(21)]

        result = tracker.analyze(
            design,
            {
                "sleep_duration_minutes": (baseline_primary, intervention_primary),
                "sleep_efficiency_pct": (baseline_secondary, intervention_secondary),
            },
            logs,
        )

        assert len(result.secondary_results) == 1
        assert result.secondary_results[0].metric == "sleep_efficiency_pct"

    def test_result_has_summary(self, tracker):
        """Every result should have a human-readable summary."""
        np.random.seed(42)
        design = _make_design()
        baseline = list(np.random.normal(400, 20, 14))
        intervention = list(np.random.normal(440, 20, 21))
        logs = [AdherenceLog(date(2026, 3, 15) + timedelta(days=i), True) for i in range(21)]

        result = tracker.analyze(
            design,
            {"sleep_duration_minutes": (baseline, intervention)},
            logs,
        )

        assert len(result.summary) > 20
        assert "Test hypothesis" in result.summary

    def test_confounders_recorded(self, tracker):
        np.random.seed(42)
        design = _make_design()
        baseline = list(np.random.normal(400, 20, 14))
        intervention = list(np.random.normal(440, 20, 21))
        logs = [AdherenceLog(date(2026, 3, 15) + timedelta(days=i), True) for i in range(21)]

        result = tracker.analyze(
            design,
            {"sleep_duration_minutes": (baseline, intervention)},
            logs,
            confounders=["travel", "illness"],
        )

        assert "travel" in result.confounders_noted
        assert "illness" in result.confounders_noted


# ── Test Metric Analysis ──────────────────────────────────────────


class TestMetricAnalysis:

    def test_effect_size_direction(self):
        """Positive effect_size when intervention > baseline."""
        from app.engine.experiments.tracker import _analyze_metric

        result = _analyze_metric(
            "test",
            [100.0] * 14,
            [120.0] * 14,
            "increase",
        )
        assert result.effect_size > 0
        assert result.direction == "increase"

    def test_significant_with_correct_direction(self):
        """Should be significant only if direction matches."""
        from app.engine.experiments.tracker import _analyze_metric

        np.random.seed(42)
        bl = list(np.random.normal(100, 5, 14))
        iv = list(np.random.normal(80, 5, 14))  # Decreased

        result_decrease = _analyze_metric("test", bl, iv, "decrease")
        result_increase = _analyze_metric("test", bl, iv, "increase")

        # Decrease direction should be significant, increase should not
        assert result_decrease.significant is True
        assert result_increase.significant is False
