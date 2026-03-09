"""Tests for Phase 2.2: Bayesian confidence framework."""

import pytest
from app.engine.statistics.confidence import compute_bayesian_confidence, ConfidenceResult


class TestBayesianConfidence:
    """Test Bayesian confidence computation."""

    def test_no_change_low_confidence(self):
        """When observed == baseline, confidence should be ~0.5 (no evidence)."""
        result = compute_bayesian_confidence(
            observed_mean=100.0,
            baseline_center=100.0,
            baseline_spread=10.0,
            n_observations=7,
        )
        assert result.probability_real == pytest.approx(0.5, abs=0.01)
        assert result.effect_size == pytest.approx(0.0, abs=0.01)

    def test_large_change_high_confidence(self):
        """A 3-sigma shift should have very high confidence."""
        result = compute_bayesian_confidence(
            observed_mean=130.0,  # 3 std above baseline
            baseline_center=100.0,
            baseline_spread=10.0,
            n_observations=7,
        )
        assert result.probability_real > 0.95
        assert result.bayes_factor > 3.0
        assert result.effect_size > 2.0  # Large effect

    def test_small_change_high_confidence_with_data(self):
        """A 1-sigma shift with 7 observations should yield high confidence."""
        result = compute_bayesian_confidence(
            observed_mean=110.0,  # 1 std above baseline
            baseline_center=100.0,
            baseline_spread=10.0,
            n_observations=7,
        )
        # With 7 observations, a 1-sigma shift is quite convincing in Bayesian terms
        assert result.probability_real > 0.9
        assert result.effect_size == pytest.approx(1.0, abs=0.01)

    def test_more_observations_increases_confidence(self):
        """More data points should increase confidence for the same effect."""
        result_few = compute_bayesian_confidence(
            observed_mean=115.0,
            baseline_center=100.0,
            baseline_spread=10.0,
            n_observations=3,
        )
        result_many = compute_bayesian_confidence(
            observed_mean=115.0,
            baseline_center=100.0,
            baseline_spread=10.0,
            n_observations=30,
        )
        assert result_many.probability_real > result_few.probability_real

    def test_credible_intervals_nested(self):
        """80% CI should be inside 95% CI."""
        result = compute_bayesian_confidence(
            observed_mean=110.0,
            baseline_center=100.0,
            baseline_spread=10.0,
            n_observations=14,
        )
        assert result.credible_interval_95[0] <= result.credible_interval_80[0]
        assert result.credible_interval_80[1] <= result.credible_interval_95[1]

    def test_negative_direction(self):
        """Should work for decreases too."""
        result = compute_bayesian_confidence(
            observed_mean=70.0,  # 3 std below baseline
            baseline_center=100.0,
            baseline_spread=10.0,
            n_observations=7,
        )
        assert result.probability_real > 0.95
        assert result.effect_size > 2.0

    def test_interpretation_categories(self):
        """Should produce valid interpretation strings."""
        # High confidence, large effect
        r1 = compute_bayesian_confidence(
            observed_mean=150.0, baseline_center=100.0,
            baseline_spread=10.0, n_observations=14,
        )
        assert "high confidence" in r1.interpretation
        assert "large" in r1.interpretation

        # Low confidence, small effect
        r2 = compute_bayesian_confidence(
            observed_mean=102.0, baseline_center=100.0,
            baseline_spread=10.0, n_observations=3,
        )
        assert "effect" in r2.interpretation

    def test_constant_baseline_handled(self):
        """Zero baseline spread shouldn't cause division by zero."""
        result = compute_bayesian_confidence(
            observed_mean=105.0,
            baseline_center=100.0,
            baseline_spread=0.0,
            n_observations=7,
        )
        assert result is not None
        assert result.probability_real > 0.5

    def test_frozen_dataclass(self):
        """ConfidenceResult should be immutable."""
        result = compute_bayesian_confidence(
            observed_mean=110.0, baseline_center=100.0,
            baseline_spread=10.0, n_observations=7,
        )
        with pytest.raises(AttributeError):
            result.probability_real = 0.99

    def test_bayes_factor_interpretation(self):
        """BF > 3 = substantial, > 10 = strong evidence."""
        # Strong effect should have high BF
        result = compute_bayesian_confidence(
            observed_mean=140.0, baseline_center=100.0,
            baseline_spread=10.0, n_observations=14,
        )
        assert result.bayes_factor > 10.0

    def test_effect_size_categories(self):
        """Effect size should match Cohen's d conventions."""
        # Small effect (d ≈ 0.3)
        r_small = compute_bayesian_confidence(
            observed_mean=103.0, baseline_center=100.0,
            baseline_spread=10.0, n_observations=14,
        )
        assert r_small.effect_size == pytest.approx(0.3, abs=0.05)

        # Medium effect (d ≈ 0.5)
        r_med = compute_bayesian_confidence(
            observed_mean=105.0, baseline_center=100.0,
            baseline_spread=10.0, n_observations=14,
        )
        assert r_med.effect_size == pytest.approx(0.5, abs=0.05)

        # Large effect (d ≈ 0.8)
        r_large = compute_bayesian_confidence(
            observed_mean=108.0, baseline_center=100.0,
            baseline_spread=10.0, n_observations=14,
        )
        assert r_large.effect_size == pytest.approx(0.8, abs=0.05)
