"""Tests for Phase 6.1: Experiment Design Engine."""

import pytest
from datetime import date, timedelta

from app.engine.experiments.designer import (
    ExperimentDesigner,
    ExperimentDesign,
    ExperimentPhase,
    PowerAnalysisResult,
    SuccessCriteria,
    power_analysis,
    INTERVENTION_METRICS,
    DEFAULT_BASELINE_DAYS,
    DEFAULT_WASHOUT_DAYS,
    MIN_INTERVENTION_DAYS,
    MAX_INTERVENTION_DAYS,
    DEFAULT_EFFECT_SIZE,
    DEFAULT_POWER,
    DEFAULT_ALPHA,
    MIN_ADHERENCE,
)


# ── Test Power Analysis ────────────────────────────────────────────


class TestPowerAnalysis:
    """Test statistical power analysis for experiment duration."""

    def test_returns_valid_result(self):
        result = power_analysis(baseline_std=10.0, effect_size=0.5)
        assert isinstance(result, PowerAnalysisResult)
        assert result.required_days >= MIN_INTERVENTION_DAYS
        assert result.power == DEFAULT_POWER
        assert result.alpha == DEFAULT_ALPHA

    def test_larger_effect_needs_fewer_days(self):
        """A larger effect should require fewer days to detect."""
        small = power_analysis(baseline_std=10.0, effect_size=0.3)
        large = power_analysis(baseline_std=10.0, effect_size=0.8)
        assert large.required_days <= small.required_days

    def test_higher_power_needs_more_days(self):
        """Higher power should require more days."""
        low = power_analysis(baseline_std=10.0, effect_size=0.5, power=0.7)
        high = power_analysis(baseline_std=10.0, effect_size=0.5, power=0.95)
        assert high.required_days >= low.required_days

    def test_minimum_days_enforced(self):
        """Should never go below MIN_INTERVENTION_DAYS."""
        result = power_analysis(baseline_std=10.0, effect_size=5.0)  # Huge effect
        assert result.required_days >= MIN_INTERVENTION_DAYS

    def test_maximum_days_enforced(self):
        """Should never exceed MAX_INTERVENTION_DAYS."""
        result = power_analysis(baseline_std=10.0, effect_size=0.01)  # Tiny effect
        assert result.required_days <= MAX_INTERVENTION_DAYS

    def test_zero_effect_raises(self):
        with pytest.raises(ValueError, match="effect_size must be positive"):
            power_analysis(baseline_std=10.0, effect_size=0.0)

    def test_negative_std_raises(self):
        with pytest.raises(ValueError, match="baseline_std must be non-negative"):
            power_analysis(baseline_std=-1.0)

    def test_zero_std_works(self):
        """Zero variance should still produce a valid result."""
        result = power_analysis(baseline_std=0.0, effect_size=0.5)
        assert result.required_days >= MIN_INTERVENTION_DAYS

    def test_method_is_set(self):
        result = power_analysis(baseline_std=10.0)
        assert result.method == "paired_t_test_nof1"


# ── Test Experiment Designer ───────────────────────────────────────


class TestExperimentDesigner:
    """Test experiment design generation."""

    @pytest.fixture
    def designer(self):
        return ExperimentDesigner()

    def test_basic_design(self, designer):
        design = designer.design(
            hypothesis="Magnesium improves sleep",
            intervention="Magnesium glycinate 400mg",
            intervention_key="magnesium_glycinate",
            target_metrics=["sleep_duration_minutes"],
            baseline_std=30.0,
        )

        assert isinstance(design, ExperimentDesign)
        assert design.hypothesis == "Magnesium improves sleep"
        assert design.intervention_key == "magnesium_glycinate"
        assert design.baseline_days >= 7
        assert design.intervention_days >= MIN_INTERVENTION_DAYS
        assert design.total_days == design.baseline_days + design.intervention_days + design.washout_days

    def test_design_has_success_criteria(self, designer):
        design = designer.design(
            hypothesis="Test",
            intervention="Test intervention",
            intervention_key="test",
            target_metrics=["sleep_duration_minutes", "sleep_efficiency_pct"],
        )

        assert design.success_criteria.primary_metric == "sleep_duration_minutes"
        assert design.success_criteria.secondary_metrics == ["sleep_efficiency_pct"]
        assert design.success_criteria.min_adherence == MIN_ADHERENCE
        assert design.success_criteria.min_effect_size > 0

    def test_design_has_power_analysis(self, designer):
        design = designer.design(
            hypothesis="Test",
            intervention="Test",
            intervention_key="test",
            target_metrics=["hrv_rmssd_ms"],
            baseline_std=12.0,
        )

        assert design.power_analysis is not None
        assert design.power_analysis.required_days == design.intervention_days

    def test_estimated_completion(self, designer):
        start = date(2026, 3, 1)
        design = designer.design(
            hypothesis="Test",
            intervention="Test",
            intervention_key="test",
            target_metrics=["hrv"],
            start_date=start,
        )

        assert design.designed_date == start
        assert design.estimated_completion == start + timedelta(days=design.total_days)

    def test_empty_metrics_raises(self, designer):
        with pytest.raises(ValueError, match="At least one target metric"):
            designer.design(
                hypothesis="Test",
                intervention="Test",
                intervention_key="test",
                target_metrics=[],
            )

    def test_invalid_direction_raises(self, designer):
        with pytest.raises(ValueError, match="direction"):
            designer.design(
                hypothesis="Test",
                intervention="Test",
                intervention_key="test",
                target_metrics=["hrv"],
                direction="sideways",
            )

    def test_confounders_included(self, designer):
        design = designer.design(
            hypothesis="Test",
            intervention="Test",
            intervention_key="test",
            target_metrics=["hrv"],
        )
        assert len(design.confounders_to_monitor) > 0
        assert "sleep_quality" in design.confounders_to_monitor

    def test_tracking_requirements(self, designer):
        design = designer.design(
            hypothesis="Test",
            intervention="Test",
            intervention_key="test",
            target_metrics=["hrv"],
        )
        assert "daily_checkin" in design.tracking_requirements
        assert "intervention_log" in design.tracking_requirements

    def test_custom_effect_size(self, designer):
        design = designer.design(
            hypothesis="Test",
            intervention="Test",
            intervention_key="test",
            target_metrics=["hrv"],
            effect_size=0.3,
        )
        assert design.success_criteria.min_effect_size == 0.3

    def test_zero_washout(self, designer):
        design = designer.design(
            hypothesis="Test",
            intervention="Test",
            intervention_key="test",
            target_metrics=["hrv"],
            washout_days=0,
        )
        assert design.washout_days == 0
        assert design.total_days == design.baseline_days + design.intervention_days


# ── Test Suggest Design ───────────────────────────────────────────


class TestSuggestDesign:

    def test_known_intervention(self):
        designer = ExperimentDesigner()
        design = designer.suggest_design("magnesium_glycinate")

        assert design is not None
        assert design.intervention_key == "magnesium_glycinate"
        assert "sleep_duration_minutes" in design.target_metrics

    def test_unknown_intervention_returns_none(self):
        designer = ExperimentDesigner()
        result = designer.suggest_design("unknown_supplement")
        assert result is None

    def test_all_known_interventions_have_designs(self):
        designer = ExperimentDesigner()
        for key in INTERVENTION_METRICS:
            design = designer.suggest_design(key)
            assert design is not None, f"No design for {key}"
            assert len(design.target_metrics) >= 1
