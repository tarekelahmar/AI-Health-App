"""Tests for Phase 2.3: Change point detection using PELT."""

import pytest
import numpy as np
from datetime import datetime, timedelta
from app.engine.detectors.change_point_detector import (
    detect_change_points,
    ChangePointResult,
)


class TestChangePointDetection:
    """Test PELT-based change point detection."""

    def _make_series_with_shift(self, n_before=20, n_after=20, mean1=50, mean2=70, std=5):
        """Create a synthetic series with one clear change point."""
        np.random.seed(42)
        before = np.random.normal(mean1, std, n_before)
        after = np.random.normal(mean2, std, n_after)
        return list(np.concatenate([before, after]))

    def test_detects_single_shift(self):
        """Should detect a clear mean shift."""
        values = self._make_series_with_shift(mean1=50, mean2=70, std=5)
        result = detect_change_points(metric_key="resting_hr", values=values)

        assert result is not None
        assert len(result.change_points) >= 1
        # The detected change point should be near index 20
        cp = result.change_points[0]
        assert 15 <= cp.index <= 25
        assert cp.direction == "increase"
        assert cp.magnitude > 10

    def test_no_change_in_stable_series(self):
        """Should detect no change points in stable data."""
        np.random.seed(42)
        values = list(np.random.normal(50, 5, 40))
        result = detect_change_points(metric_key="resting_hr", values=values)

        assert result is not None
        assert len(result.change_points) == 0

    def test_decrease_direction(self):
        """Should detect decreasing shifts."""
        values = self._make_series_with_shift(mean1=70, mean2=50, std=5)
        result = detect_change_points(metric_key="hrv_rmssd", values=values)

        assert result is not None
        assert len(result.change_points) >= 1
        cp = result.change_points[0]
        assert cp.direction == "decrease"

    def test_insufficient_data_returns_none(self):
        """Should return None with too few points."""
        values = [1.0, 2.0, 3.0]  # < min_segment_size * 2
        result = detect_change_points(metric_key="resting_hr", values=values)
        assert result is None

    def test_confidence_scales_with_effect(self):
        """Larger shifts should have higher confidence."""
        small_shift = self._make_series_with_shift(mean1=50, mean2=55, std=5)
        large_shift = self._make_series_with_shift(mean1=50, mean2=75, std=5)

        r_small = detect_change_points(metric_key="test", values=small_shift)
        r_large = detect_change_points(metric_key="test", values=large_shift)

        if r_small and r_small.change_points and r_large and r_large.change_points:
            assert r_large.change_points[0].confidence >= r_small.change_points[0].confidence

    def test_timestamps_preserved(self):
        """Should carry timestamps through to change points."""
        values = self._make_series_with_shift(mean1=50, mean2=70, std=5)
        base = datetime(2026, 1, 1)
        timestamps = [base + timedelta(days=i) for i in range(len(values))]

        result = detect_change_points(
            metric_key="resting_hr",
            values=values,
            timestamps=timestamps,
        )

        assert result is not None
        if result.change_points:
            assert result.change_points[0].timestamp is not None

    def test_multiple_change_points(self):
        """Should detect multiple regime shifts."""
        np.random.seed(42)
        segment1 = np.random.normal(50, 3, 20)
        segment2 = np.random.normal(70, 3, 20)
        segment3 = np.random.normal(40, 3, 20)
        values = list(np.concatenate([segment1, segment2, segment3]))

        result = detect_change_points(metric_key="hrv_rmssd", values=values)

        assert result is not None
        assert len(result.change_points) >= 2

    def test_min_segment_size_respected(self):
        """Change points should respect minimum segment size."""
        values = self._make_series_with_shift(n_before=20, n_after=20)
        result = detect_change_points(
            metric_key="test",
            values=values,
            min_segment_size=7,
        )

        assert result is not None
        # All segments should be at least 7 points
        if result.change_points:
            for cp in result.change_points:
                assert cp.index >= 7

    def test_binseg_method(self):
        """Binary segmentation should also work."""
        values = self._make_series_with_shift(mean1=50, mean2=70, std=5)
        result = detect_change_points(
            metric_key="test",
            values=values,
            method="binseg",
        )

        assert result is not None
        assert result.method == "binseg"

    def test_unknown_method_raises(self):
        """Should raise ValueError for unknown method."""
        with pytest.raises(ValueError, match="Unknown change point method"):
            detect_change_points(
                metric_key="test",
                values=[1.0] * 20,
                method="nonexistent",
            )

    def test_result_frozen(self):
        """ChangePointResult should be frozen."""
        values = self._make_series_with_shift()
        result = detect_change_points(metric_key="test", values=values)
        assert result is not None
        with pytest.raises(AttributeError):
            result.metric_key = "hacked"

    def test_before_after_stats(self):
        """Change point should include segment statistics."""
        values = self._make_series_with_shift(mean1=50, mean2=70, std=5)
        result = detect_change_points(metric_key="test", values=values)

        assert result is not None
        if result.change_points:
            cp = result.change_points[0]
            assert 40 < cp.before_mean < 60  # Near 50
            assert 60 < cp.after_mean < 80  # Near 70
            assert cp.before_std > 0
            assert cp.after_std > 0
