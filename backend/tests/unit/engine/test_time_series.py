"""Comprehensive tests for time series analytics"""
import pytest
from datetime import datetime, date, timedelta
from unittest.mock import Mock

from app.engine.analytics.time_series import (
    MetricPoint,
    DailyMetric,
    _aggregate_by_day,
    build_wearable_daily_series,
    build_lab_daily_series,
    build_health_data_daily_series,
    merge_daily_series,
    to_dict_series,
)


class TestMetricPoint:
    """Test MetricPoint dataclass"""
    
    def test_metric_point_creation(self):
        """Test creating a MetricPoint"""
        point = MetricPoint(
            timestamp=datetime(2024, 1, 1, 12, 0),
            value=75.5
        )
        assert point.timestamp == datetime(2024, 1, 1, 12, 0)
        assert point.value == 75.5


class TestDailyMetric:
    """Test DailyMetric dataclass"""
    
    def test_daily_metric_creation(self):
        """Test creating a DailyMetric"""
        metric = DailyMetric(
            date=date(2024, 1, 1),
            value=75.5,
            count=3
        )
        assert metric.date == date(2024, 1, 1)
        assert metric.value == 75.5
        assert metric.count == 3


class TestAggregateByDay:
    """Test _aggregate_by_day function"""
    
    def test_aggregate_mean_single_day(self):
        """Test mean aggregation for single day with multiple points"""
        points = [
            MetricPoint(timestamp=datetime(2024, 1, 1, 8, 0), value=70.0),
            MetricPoint(timestamp=datetime(2024, 1, 1, 12, 0), value=80.0),
            MetricPoint(timestamp=datetime(2024, 1, 1, 18, 0), value=90.0),
        ]
        result = _aggregate_by_day(points, aggregation="mean")
        
        assert len(result) == 1
        assert result[0].date == date(2024, 1, 1)
        assert result[0].value == 80.0  # (70 + 80 + 90) / 3
        assert result[0].count == 3
    
    def test_aggregate_sum(self):
        """Test sum aggregation"""
        points = [
            MetricPoint(timestamp=datetime(2024, 1, 1, 8, 0), value=10.0),
            MetricPoint(timestamp=datetime(2024, 1, 1, 12, 0), value=20.0),
        ]
        result = _aggregate_by_day(points, aggregation="sum")
        
        assert len(result) == 1
        assert result[0].value == 30.0
        assert result[0].count == 2
    
    def test_aggregate_last(self):
        """Test last aggregation (takes last value)"""
        points = [
            MetricPoint(timestamp=datetime(2024, 1, 1, 8, 0), value=10.0),
            MetricPoint(timestamp=datetime(2024, 1, 1, 12, 0), value=20.0),
            MetricPoint(timestamp=datetime(2024, 1, 1, 18, 0), value=30.0),
        ]
        result = _aggregate_by_day(points, aggregation="last")
        
        assert len(result) == 1
        assert result[0].value == 30.0  # Last value
        assert result[0].count == 3
    
    def test_aggregate_multiple_days(self):
        """Test aggregation across multiple days"""
        points = [
            MetricPoint(timestamp=datetime(2024, 1, 1, 12, 0), value=10.0),
            MetricPoint(timestamp=datetime(2024, 1, 2, 12, 0), value=20.0),
            MetricPoint(timestamp=datetime(2024, 1, 3, 12, 0), value=30.0),
        ]
        result = _aggregate_by_day(points, aggregation="mean")
        
        assert len(result) == 3
        assert result[0].date == date(2024, 1, 1)
        assert result[0].value == 10.0
        assert result[1].date == date(2024, 1, 2)
        assert result[1].value == 20.0
        assert result[2].date == date(2024, 1, 3)
        assert result[2].value == 30.0
    
    def test_aggregate_empty_list(self):
        """Test aggregation with empty list"""
        result = _aggregate_by_day([], aggregation="mean")
        assert result == []
    
    def test_aggregate_sorted_by_date(self):
        """Test that results are sorted by date"""
        points = [
            MetricPoint(timestamp=datetime(2024, 1, 3, 12, 0), value=30.0),
            MetricPoint(timestamp=datetime(2024, 1, 1, 12, 0), value=10.0),
            MetricPoint(timestamp=datetime(2024, 1, 2, 12, 0), value=20.0),
        ]
        result = _aggregate_by_day(points, aggregation="mean")
        
        assert len(result) == 3
        assert result[0].date < result[1].date < result[2].date


class TestBuildWearableDailySeries:
    """Test build_wearable_daily_series function"""
    
    def test_build_series_with_data(self):
        """Test building series from wearable repository"""
        mock_repo = Mock()
        mock_samples = [
            Mock(timestamp=datetime(2024, 1, 1, 8, 0), value=70.0),
            Mock(timestamp=datetime(2024, 1, 1, 12, 0), value=80.0),
            Mock(timestamp=datetime(2024, 1, 2, 8, 0), value=75.0),
        ]
        mock_repo.list_for_user_in_range.return_value = mock_samples
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 3)
        
        result = build_wearable_daily_series(
            user_id=1,
            metric_type="hrv",
            start=start,
            end=end,
            wearable_repo=mock_repo,
            aggregation="mean",
        )
        
        assert len(result) == 2
        assert result[0].date == date(2024, 1, 1)
        assert result[0].value == 75.0  # (70 + 80) / 2
        assert result[1].date == date(2024, 1, 2)
        assert result[1].value == 75.0
    
    def test_build_series_no_data(self):
        """Test building series when no data exists"""
        mock_repo = Mock()
        mock_repo.list_for_user_in_range.return_value = []
        
        result = build_wearable_daily_series(
            user_id=1,
            metric_type="hrv",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 3),
            wearable_repo=mock_repo,
        )
        
        assert result == []
    
    def test_build_series_calls_repo_correctly(self):
        """Test that repository is called with correct parameters"""
        mock_repo = Mock()
        mock_repo.list_for_user_in_range.return_value = []
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 3)
        
        build_wearable_daily_series(
            user_id=1,
            metric_type="sleep_duration",
            start=start,
            end=end,
            wearable_repo=mock_repo,
        )
        
        mock_repo.list_for_user_in_range.assert_called_once_with(
            user_id=1,
            start=start,
            end=end,
            metric_type="sleep_duration",
        )


class TestBuildLabDailySeries:
    """Test build_lab_daily_series function"""
    
    def test_build_lab_series(self):
        """Test building series from lab repository"""
        mock_repo = Mock()
        mock_results = [
            Mock(timestamp=datetime(2024, 1, 1, 10, 0), value=100.0),
            Mock(timestamp=datetime(2024, 1, 2, 10, 0), value=110.0),
        ]
        mock_repo.list_for_user_in_range.return_value = mock_results
        
        result = build_lab_daily_series(
            user_id=1,
            test_name="glucose",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 3),
            lab_repo=mock_repo,
            aggregation="last",
        )
        
        assert len(result) == 2
        assert result[0].value == 100.0
        assert result[1].value == 110.0


class TestBuildHealthDataDailySeries:
    """Test build_health_data_daily_series function"""
    
    def test_build_health_data_series(self):
        """Test building series from health data repository"""
        mock_repo = Mock()
        mock_points = [
            Mock(timestamp=datetime(2024, 1, 1, 8, 0), value=50.0),
            Mock(timestamp=datetime(2024, 1, 1, 12, 0), value=60.0),
        ]
        mock_repo.get_by_time_range.return_value = mock_points
        
        result = build_health_data_daily_series(
            user_id=1,
            data_type="stress_score",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 3),
            health_data_repo=mock_repo,
            aggregation="mean",
        )
        
        assert len(result) == 1
        assert result[0].value == 55.0  # (50 + 60) / 2


class TestMergeDailySeries:
    """Test merge_daily_series function"""
    
    def test_merge_two_series(self):
        """Test merging two series with overlapping dates"""
        series1 = [
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
            DailyMetric(date=date(2024, 1, 2), value=20.0, count=1),
        ]
        series2 = [
            DailyMetric(date=date(2024, 1, 1), value=30.0, count=1),
            DailyMetric(date=date(2024, 1, 3), value=40.0, count=1),
        ]
        
        result = merge_daily_series([series1, series2], aggregation="mean")
        
        assert len(result) == 3
        # Jan 1: (10 + 30) / 2 = 20
        assert result[0].date == date(2024, 1, 1)
        assert result[0].value == 20.0
        # Jan 2: 20
        assert result[1].date == date(2024, 1, 2)
        assert result[1].value == 20.0
        # Jan 3: 40
        assert result[2].date == date(2024, 1, 3)
        assert result[2].value == 40.0
    
    def test_merge_empty_series(self):
        """Test merging empty series"""
        result = merge_daily_series([], aggregation="mean")
        assert result == []
    
    def test_merge_single_series(self):
        """Test merging single series (should return same)"""
        series = [
            DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
        ]
        result = merge_daily_series([series], aggregation="mean")
        assert len(result) == 1
        assert result[0].value == 10.0


class TestToDictSeries:
    """Test to_dict_series utility function"""
    
    def test_convert_to_dict(self):
        """Test converting DailyMetric list to dict list"""
        series = [
            DailyMetric(date=date(2024, 1, 1), value=75.5, count=3),
            DailyMetric(date=date(2024, 1, 2), value=80.0, count=2),
        ]
        
        result = to_dict_series(series)
        
        assert len(result) == 2
        assert result[0]["date"] == "2024-01-01"
        assert result[0]["value"] == 75.5
        assert result[0]["count"] == 3
        assert result[1]["date"] == "2024-01-02"
        assert result[1]["value"] == 80.0
    
    def test_convert_empty_series(self):
        """Test converting empty series"""
        result = to_dict_series([])
        assert result == []

