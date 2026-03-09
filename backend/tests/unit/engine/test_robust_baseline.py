"""Tests for Phase 2.1: Robust baseline estimation."""

import pytest
import numpy as np
from app.engine.statistics.robust_baseline import estimate_baseline, BaselineEstimate


class TestEstimateBaseline:
    """Test the core robust estimation function."""

    def test_median_mad_basic(self):
        """Median/MAD should return stable center and spread."""
        values = [100, 102, 98, 101, 99, 103, 97, 100, 101, 98]
        result = estimate_baseline(values, method="median_mad")

        assert result is not None
        assert result.method == "median_mad"
        assert result.n_samples == 10
        assert 98 <= result.center <= 102  # Median should be near 100
        assert result.spread > 0

    def test_median_mad_outlier_resistant(self):
        """Median/MAD should resist outliers better than mean/std."""
        # Normal values ~100, one extreme outlier at 500
        values = [100, 102, 98, 101, 99, 103, 97, 100, 101, 500]

        robust = estimate_baseline(values, method="median_mad")
        simple = estimate_baseline(values, method="mean_std")

        assert robust is not None
        assert simple is not None

        # Robust center should be near 100 (outlier ignored)
        assert 98 <= robust.center <= 102
        # Simple mean is pulled toward outlier
        assert simple.center > 120

        # Robust spread should be much smaller than simple std
        assert robust.spread < simple.spread

    def test_trimmed_mean(self):
        """Trimmed mean should also resist outliers."""
        values = [100, 102, 98, 101, 99, 103, 97, 100, 101, 500]
        result = estimate_baseline(values, method="trimmed_mean")

        assert result is not None
        assert result.method == "trimmed_mean"
        # Trimmed mean should be closer to 100 than simple mean
        assert result.center < 120

    def test_mean_std_fallback(self):
        """Legacy mean_std method should still work."""
        values = [100, 102, 98, 101, 99]
        result = estimate_baseline(values, method="mean_std")

        assert result is not None
        assert result.method == "mean_std"
        assert abs(result.center - 100) < 2

    def test_confidence_intervals(self):
        """CI should be computed and nested properly."""
        values = list(range(50, 80))  # 30 values
        result = estimate_baseline(values, method="median_mad")

        assert result is not None
        # CI 80 should be inside CI 95
        assert result.ci_95[0] <= result.ci_80[0]
        assert result.ci_80[1] <= result.ci_95[1]
        # Center should be inside both CIs
        assert result.ci_80[0] <= result.center <= result.ci_80[1]
        assert result.ci_95[0] <= result.center <= result.ci_95[1]

    def test_stability_flag(self):
        """is_stable should be True when n >= 14."""
        short = estimate_baseline([1, 2, 3, 4, 5])
        long = estimate_baseline(list(range(20)))

        assert short is not None
        assert long is not None
        assert short.is_stable is False
        assert long.is_stable is True

    def test_insufficient_data_returns_none(self):
        """Should return None if fewer than min_samples."""
        result = estimate_baseline([1, 2, 3, 4])  # 4 < 5 default
        assert result is None

    def test_constant_data(self):
        """Should handle constant data without division by zero."""
        values = [42.0] * 10
        result = estimate_baseline(values, method="median_mad")

        assert result is not None
        assert result.center == 42.0
        assert result.spread > 0  # Should be clamped to small positive

    def test_unknown_method_raises(self):
        """Should raise ValueError for unknown method."""
        with pytest.raises(ValueError, match="Unknown baseline method"):
            estimate_baseline([1, 2, 3, 4, 5], method="nonexistent")

    def test_frozen_dataclass(self):
        """BaselineEstimate should be immutable."""
        result = estimate_baseline([1, 2, 3, 4, 5])
        assert result is not None
        with pytest.raises(AttributeError):
            result.center = 999

    def test_large_dataset_performance(self):
        """Should handle large datasets without issues."""
        np.random.seed(42)
        values = list(np.random.normal(60, 10, 365))  # 1 year of daily data
        result = estimate_baseline(values, method="median_mad")

        assert result is not None
        assert result.n_samples == 365
        assert result.is_stable is True
        assert 55 <= result.center <= 65

    def test_negative_values(self):
        """Should work with negative values (e.g., temperature deviations)."""
        values = [-0.5, -0.3, -0.1, 0.1, 0.3, -0.2, 0.0, -0.4, 0.2, -0.1]
        result = estimate_baseline(values, method="median_mad")

        assert result is not None
        assert -0.5 <= result.center <= 0.5
