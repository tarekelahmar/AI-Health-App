"""Comprehensive tests for rolling metrics"""
import pytest
from datetime import date

from app.engine.analytics.rolling_metrics import (
    RollingStat,
    _compute_basic_stats,
    compute_rolling_stats,
    to_dict_series,
)
from app.engine.analytics.time_series import DailyMetric


class TestComputeBasicStats:
    """Test _compute_basic_stats function"""
    
    def test_compute_stats_normal_case(self):
        """Test computing stats for normal values"""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = _compute_basic_stats(values)
        
        assert stats["mean"] == 30.0
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["std"] > 0  # Should have some variance
    
    def test_compute_stats_single_value(self):
        """Test computing stats for single value"""
        values = [42.0]
        stats = _compute_basic_stats(values)
        
        assert stats["mean"] == 42.0
        assert stats["min"] == 42.0
        assert stats["max"] == 42.0
        assert stats["std"] == 0.0  # No variance with single value
    
    def test_compute_stats_empty_list(self):
        """Test computing stats for empty list"""
        stats = _compute_basic_stats([])
        
        assert stats["mean"] == 0.0
        assert stats["min"] == 0.0
        assert stats["max"] == 0.0
        assert stats["std"] == 0.0
    
    def test_compute_stats_negative_values(self):
        """Test computing stats with negative values"""
        values = [-10.0, 0.0, 10.0]
        stats = _compute_basic_stats(values)
        
        assert stats["mean"] == 0.0
        assert stats["min"] == -10.0
        assert stats["max"] == 10.0


class TestComputeRollingStats:
    """Test compute_rolling_stats function"""
    
    def test_rolling_stats_window_7(self):
        """Test rolling stats with window size 7"""
        series = [
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
            DailyMetric(date=date(2024, 1, 2), value=20.0, count=1),
            DailyMetric(date=date(2024, 1, 3), value=30.0, count=1),
            DailyMetric(date=date(2024, 1, 4), value=40.0, count=1),
            DailyMetric(date=date(2024, 1, 5), value=50.0, count=1),
        ]
        
        result = compute_rolling_stats(series, window_size=7)
        
        assert len(result) == 5
        # First value: only itself
        assert result[0].mean == 10.0
        # Second value: average of first two
        assert result[1].mean == 15.0
        # Last value: average of all five
        assert result[4].mean == 30.0
    
    def test_rolling_stats_window_3(self):
        """Test rolling stats with smaller window"""
        series = [
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
            DailyMetric(date=date(2024, 1, 2), value=20.0, count=1),
            DailyMetric(date=date(2024, 1, 3), value=30.0, count=1),
            DailyMetric(date=date(2024, 1, 4), value=40.0, count=1),
        ]
        
        result = compute_rolling_stats(series, window_size=3)
        
        assert len(result) == 4
        # Third value: average of first three
        assert result[2].mean == 20.0
        # Fourth value: average of last three (2, 3, 4)
        assert result[3].mean == 30.0
    
    def test_rolling_stats_unsorted(self):
        """Test that series is sorted before computing"""
        series = [
            DailyMetric(date=date(2024, 1, 3), value=30.0, count=1),
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
            DailyMetric(date=date(2024, 1, 2), value=20.0, count=1),
        ]
        
        result = compute_rolling_stats(series, window_size=3)
        
        assert len(result) == 3
        # Should be sorted by date
        assert result[0].date == "2024-01-01"
        assert result[1].date == "2024-01-02"
        assert result[2].date == "2024-01-03"
    
    def test_rolling_stats_empty_series(self):
        """Test with empty series"""
        result = compute_rolling_stats([], window_size=7)
        assert result == []
    
    def test_rolling_stats_single_value(self):
        """Test with single value"""
        series = [
            DailyMetric(date=date(2024, 1, 1), value=42.0, count=1),
        ]
        
        result = compute_rolling_stats(series, window_size=7)
        
        assert len(result) == 1
        assert result[0].mean == 42.0
        assert result[0].std == 0.0
        assert result[0].minimum == 42.0
        assert result[0].maximum == 42.0
        assert result[0].count == 1
    
    def test_rolling_stats_invalid_window(self):
        """Test with invalid window size"""
        series = [
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
        ]
        
        with pytest.raises(ValueError):
            compute_rolling_stats(series, window_size=0)
        
        with pytest.raises(ValueError):
            compute_rolling_stats(series, window_size=-1)
    
    def test_rolling_stats_std_calculation(self):
        """Test that standard deviation is calculated correctly"""
        series = [
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
            DailyMetric(date=date(2024, 1, 2), value=20.0, count=1),
            DailyMetric(date=date(2024, 1, 3), value=30.0, count=1),
        ]
        
        result = compute_rolling_stats(series, window_size=3)
        
        # Last value should have std > 0 (variance in values)
        assert result[2].std > 0
        # First value should have std = 0 (only one value)
        assert result[0].std == 0.0


class TestToDictSeries:
    """Test to_dict_series function"""
    
    def test_convert_to_dict(self):
        """Test converting RollingStat list to dict list"""
        stats = [
            RollingStat(
                date="2024-01-01",
                mean=25.0,
                std=5.0,
                minimum=20.0,
                maximum=30.0,
                count=3,
            ),
            RollingStat(
                date="2024-01-02",
                mean=35.0,
                std=7.0,
                minimum=25.0,
                maximum=45.0,
                count=5,
            ),
        ]
        
        result = to_dict_series(stats)
        
        assert len(result) == 2
        assert result[0]["date"] == "2024-01-01"
        assert result[0]["mean"] == 25.0
        assert result[0]["std"] == 5.0
        assert result[0]["min"] == 20.0
        assert result[0]["max"] == 30.0
        assert result[0]["count"] == 3
    
    def test_convert_empty_list(self):
        """Test converting empty list"""
        result = to_dict_series([])
        assert result == []

