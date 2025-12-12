"""Comprehensive tests for correlation analysis"""
import pytest
from datetime import date

from app.engine.analytics.correlation import (
    CorrelationResult,
    _align_series_by_date,
    _pearson_correlation,
    _interpret_strength,
    _is_reliable,
    compute_metric_correlation,
    to_dict,
)
from app.engine.analytics.time_series import DailyMetric


class TestAlignSeriesByDate:
    """Test _align_series_by_date function"""
    
    def test_align_perfect_overlap(self):
        """Test aligning series with perfect date overlap"""
        series_x = [
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
            DailyMetric(date=date(2024, 1, 2), value=20.0, count=1),
            DailyMetric(date=date(2024, 1, 3), value=30.0, count=1),
        ]
        series_y = [
            DailyMetric(date=date(2024, 1, 1), value=5.0, count=1),
            DailyMetric(date=date(2024, 1, 2), value=10.0, count=1),
            DailyMetric(date=date(2024, 1, 3), value=15.0, count=1),
        ]
        
        xs, ys = _align_series_by_date(series_x, series_y)
        
        assert len(xs) == 3
        assert len(ys) == 3
        assert xs == [10.0, 20.0, 30.0]
        assert ys == [5.0, 10.0, 15.0]
    
    def test_align_partial_overlap(self):
        """Test aligning series with partial overlap"""
        series_x = [
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
            DailyMetric(date=date(2024, 1, 2), value=20.0, count=1),
        ]
        series_y = [
            DailyMetric(date=date(2024, 1, 2), value=10.0, count=1),
            DailyMetric(date=date(2024, 1, 3), value=15.0, count=1),
        ]
        
        xs, ys = _align_series_by_date(series_x, series_y)
        
        assert len(xs) == 1
        assert len(ys) == 1
        assert xs == [20.0]
        assert ys == [10.0]
    
    def test_align_no_overlap(self):
        """Test aligning series with no overlap"""
        series_x = [
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
        ]
        series_y = [
            DailyMetric(date=date(2024, 1, 2), value=10.0, count=1),
        ]
        
        xs, ys = _align_series_by_date(series_x, series_y)
        
        assert len(xs) == 0
        assert len(ys) == 0
    
    def test_align_sorted_dates(self):
        """Test that aligned dates are sorted"""
        series_x = [
            DailyMetric(date=date(2024, 1, 3), value=30.0, count=1),
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
            DailyMetric(date=date(2024, 1, 2), value=20.0, count=1),
        ]
        series_y = [
            DailyMetric(date=date(2024, 1, 1), value=5.0, count=1),
            DailyMetric(date=date(2024, 1, 2), value=10.0, count=1),
            DailyMetric(date=date(2024, 1, 3), value=15.0, count=1),
        ]
        
        xs, ys = _align_series_by_date(series_x, series_y)
        
        # Should be sorted by date
        assert xs == [10.0, 20.0, 30.0]
        assert ys == [5.0, 10.0, 15.0]


class TestPearsonCorrelation:
    """Test _pearson_correlation function"""
    
    def test_perfect_positive_correlation(self):
        """Test perfect positive correlation (r = 1.0)"""
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 6.0, 8.0, 10.0]  # y = 2x
        
        r = _pearson_correlation(xs, ys)
        
        assert r is not None
        assert abs(r - 1.0) < 0.0001  # Should be very close to 1.0
    
    def test_perfect_negative_correlation(self):
        """Test perfect negative correlation (r = -1.0)"""
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [10.0, 8.0, 6.0, 4.0, 2.0]  # y = 12 - 2x
        
        r = _pearson_correlation(xs, ys)
        
        assert r is not None
        assert abs(r - (-1.0)) < 0.0001  # Should be very close to -1.0
    
    def test_no_correlation(self):
        """Test no correlation (r ≈ 0)"""
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [5.0, 3.0, 4.0, 2.0, 1.0]  # Random values
        
        r = _pearson_correlation(xs, ys)
        
        assert r is not None
        assert abs(r) < 0.5  # Should be low correlation
    
    def test_insufficient_data(self):
        """Test with insufficient data (n < 2)"""
        xs = [1.0]
        ys = [2.0]
        
        r = _pearson_correlation(xs, ys)
        
        assert r is None
    
    def test_zero_variance(self):
        """Test with zero variance (all same values)"""
        xs = [5.0, 5.0, 5.0, 5.0]
        ys = [3.0, 3.0, 3.0, 3.0]
        
        r = _pearson_correlation(xs, ys)
        
        assert r is None  # Cannot compute correlation with zero variance
    
    def test_correlation_clamped(self):
        """Test that correlation is clamped to [-1, 1]"""
        # Even with float precision issues, should be clamped
        xs = [1.0, 2.0, 3.0]
        ys = [2.0, 4.0, 6.0]
        
        r = _pearson_correlation(xs, ys)
        
        assert r is not None
        assert -1.0 <= r <= 1.0


class TestInterpretStrength:
    """Test _interpret_strength function"""
    
    def test_strong_correlation_high_n(self):
        """Test strong correlation with sufficient data"""
        strength = _interpret_strength(0.85, n=20)
        assert strength == "strong"
    
    def test_moderate_correlation_high_n(self):
        """Test moderate correlation with sufficient data"""
        strength = _interpret_strength(0.65, n=20)
        assert strength == "moderate"
    
    def test_weak_correlation_high_n(self):
        """Test weak correlation with sufficient data"""
        strength = _interpret_strength(0.4, n=20)
        assert strength == "weak"
    
    def test_none_correlation_high_n(self):
        """Test no correlation with sufficient data"""
        strength = _interpret_strength(0.2, n=20)
        assert strength == "none"
    
    def test_low_data_high_correlation(self):
        """Test high correlation with low data (should be downplayed)"""
        strength = _interpret_strength(0.85, n=5)
        assert "low data" in strength
    
    def test_low_data_moderate_correlation(self):
        """Test moderate correlation with low data"""
        strength = _interpret_strength(0.5, n=5)
        assert "low data" in strength
    
    def test_negative_correlation(self):
        """Test that negative correlation uses absolute value"""
        strength = _interpret_strength(-0.75, n=20)
        assert strength == "strong"


class TestIsReliable:
    """Test _is_reliable function"""
    
    def test_reliable_high_n_high_r(self):
        """Test reliable correlation (n >= 10, |r| >= 0.3)"""
        assert _is_reliable(0.5, n=15) is True
        assert _is_reliable(-0.4, n=20) is True
    
    def test_unreliable_low_n(self):
        """Test unreliable correlation (n < 10)"""
        assert _is_reliable(0.5, n=5) is False
        assert _is_reliable(0.8, n=9) is False
    
    def test_unreliable_low_r(self):
        """Test unreliable correlation (|r| < 0.3)"""
        assert _is_reliable(0.2, n=20) is False
        assert _is_reliable(-0.25, n=30) is False
    
    def test_unreliable_both_low(self):
        """Test unreliable correlation (both n and r low)"""
        assert _is_reliable(0.2, n=5) is False


class TestComputeMetricCorrelation:
    """Test compute_metric_correlation function"""
    
    def test_compute_valid_correlation(self):
        """Test computing correlation with valid data"""
        series_x = [
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
            DailyMetric(date=date(2024, 1, 2), value=20.0, count=1),
            DailyMetric(date=date(2024, 1, 3), value=30.0, count=1),
            DailyMetric(date=date(2024, 1, 4), value=40.0, count=1),
            DailyMetric(date=date(2024, 1, 5), value=50.0, count=1),
        ]
        series_y = [
            DailyMetric(date=date(2024, 1, 1), value=5.0, count=1),
            DailyMetric(date=date(2024, 1, 2), value=10.0, count=1),
            DailyMetric(date=date(2024, 1, 3), value=15.0, count=1),
            DailyMetric(date=date(2024, 1, 4), value=20.0, count=1),
            DailyMetric(date=date(2024, 1, 5), value=25.0, count=1),
        ]
        
        result = compute_metric_correlation(
            "metric_x",
            "metric_y",
            series_x,
            series_y,
        )
        
        assert result is not None
        assert result.metric_x == "metric_x"
        assert result.metric_y == "metric_y"
        assert result.n == 5
        assert abs(result.r - 1.0) < 0.0001  # Perfect correlation
        assert result.strength in ["strong", "moderate (low data)"]
        assert result.direction == "positive"
        assert result.is_reliable is True
    
    def test_insufficient_overlap(self):
        """Test with insufficient overlapping data (n < 3)"""
        series_x = [
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
        ]
        series_y = [
            DailyMetric(date=date(2024, 1, 1), value=5.0, count=1),
        ]
        
        result = compute_metric_correlation(
            "metric_x",
            "metric_y",
            series_x,
            series_y,
        )
        
        assert result is None
    
    def test_no_overlap(self):
        """Test with no overlapping dates"""
        series_x = [
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
        ]
        series_y = [
            DailyMetric(date=date(2024, 1, 2), value=5.0, count=1),
        ]
        
        result = compute_metric_correlation(
            "metric_x",
            "metric_y",
            series_x,
            series_y,
        )
        
        assert result is None
    
    def test_negative_correlation(self):
        """Test negative correlation"""
        series_x = [
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
            DailyMetric(date=date(2024, 1, 2), value=20.0, count=1),
            DailyMetric(date=date(2024, 1, 3), value=30.0, count=1),
        ]
        series_y = [
            DailyMetric(date=date(2024, 1, 1), value=30.0, count=1),
            DailyMetric(date=date(2024, 1, 2), value=20.0, count=1),
            DailyMetric(date=date(2024, 1, 3), value=10.0, count=1),
        ]
        
        result = compute_metric_correlation(
            "metric_x",
            "metric_y",
            series_x,
            series_y,
        )
        
        assert result is not None
        assert result.r < 0
        assert result.direction == "negative"


class TestToDict:
    """Test to_dict function"""
    
    def test_convert_to_dict(self):
        """Test converting CorrelationResult to dict"""
        result = CorrelationResult(
            metric_x="sleep_duration",
            metric_y="hrv",
            r=0.75,
            n=20,
            strength="strong",
            direction="positive",
            is_reliable=True,
        )
        
        dict_result = to_dict(result)
        
        assert dict_result["metric_x"] == "sleep_duration"
        assert dict_result["metric_y"] == "hrv"
        assert dict_result["r"] == 0.75
        assert dict_result["n"] == 20
        assert dict_result["strength"] == "strong"
        assert dict_result["direction"] == "positive"
        assert dict_result["is_reliable"] is True

