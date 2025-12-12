from datetime import datetime, timedelta
from app.engine.reasoning.insight_generator import (
    InsightEngine,
    MetricSummary,
    GeneratedInsight,
)


# -------------------------
# Fake repository classes
# -------------------------


class FakeWearableRepo:
    """
    Returns predictable wearable data:
    sleep_duration increases slightly over time.
    HRV decreases over time.
    Activity increases sharply.
    """
    def list_for_user_in_range(self, user_id, start, end, metric_type=None):
        now = datetime.utcnow()

        data_points = []

        for i in range(15):  # 15 days of data
            # Shift time backwards
            timestamp = now - timedelta(days=i)

            if metric_type == "sleep_duration":
                # Slight upward trend
                value = 6.0 + (i * 0.1)
            elif metric_type == "hrv":
                # Downward trend
                value = 70 - i
            elif metric_type == "activity_minutes":
                # Strong upward trend
                value = 40 + (i * 5)
            else:
                value = 50

            obj = type("Obj", (), {})()
            obj.timestamp = timestamp
            obj.value = value
            obj.unit = "units"
            data_points.append(obj)

        return data_points


class FakeLabRepo:
    def list_for_user_in_range(self, *args, **kwargs):
        return []  # no labs for this test


class FakeHealthRepo:
    def get_by_time_range(self, *args, **kwargs):
        return []  # no generic data points


class FakeSymptomRepo:
    pass


class FakeInsightRepo:
    """Captures saved insight for assertions."""
    def __init__(self):
        self.saved = None

    def create(self, **kwargs):
        self.saved = kwargs
        return kwargs


# -------------------------
# Tests
# -------------------------


def test_sleep_insight_generation_with_mock_data():
    """
    Core test:
    Ensures InsightEngine generates a valid sleep insight object from mock data.
    """
    fake_repo = FakeInsightRepo()

    engine = InsightEngine(
        lab_repo=FakeLabRepo(),
        wearable_repo=FakeWearableRepo(),
        health_data_repo=FakeHealthRepo(),
        symptom_repo=FakeSymptomRepo(),
        insight_repo=fake_repo,
    )

    insight = engine.generate_sleep_insights(
        user_id=1,
        window_days=14,
    )

    # Assertions on existence
    assert insight is not None, "Insight should be generated"
    assert isinstance(insight, GeneratedInsight)
    assert insight.category == "sleep"

    # Check metric summaries produced
    assert len(insight.metric_summaries) >= 1
    names = [m.metric_name for m in insight.metric_summaries]
    assert "sleep_duration" in names

    # Check correlation exists
    assert len(insight.correlations) >= 1

    # Check trend directions make sense with mock patterns
    sleep_summary = next(m for m in insight.metric_summaries if m.metric_name == "sleep_duration")
    assert sleep_summary.trend in ["improving", "worsening", "stable", "unknown"]

    # Check engine can persist to repository
    engine.persist_insight(insight)
    assert fake_repo.saved is not None
    assert fake_repo.saved["user_id"] == 1
    assert "metric_summaries" in fake_repo.saved["metadata_json"]


def test_metric_summary_structure():
    """Ensure MetricSummary structure is valid."""
    fake_repo = FakeInsightRepo()

    engine = InsightEngine(
        lab_repo=FakeLabRepo(),
        wearable_repo=FakeWearableRepo(),
        health_data_repo=FakeHealthRepo(),
        symptom_repo=FakeSymptomRepo(),
        insight_repo=fake_repo,
    )

    insight = engine.generate_sleep_insights(user_id=1, window_days=14)
    assert insight is not None

    for summary in insight.metric_summaries:
        assert summary.metric_name is not None
        assert summary.window_days == 14
        assert summary.latest_value is not None
        assert summary.mean_value is not None


def test_correlation_structure():
    """Ensure correlation objects look correct."""
    fake_repo = FakeInsightRepo()

    engine = InsightEngine(
        lab_repo=FakeLabRepo(),
        wearable_repo=FakeWearableRepo(),
        health_data_repo=FakeHealthRepo(),
        symptom_repo=FakeSymptomRepo(),
        insight_repo=fake_repo,
    )

    insight = engine.generate_sleep_insights(user_id=1, window_days=14)
    assert insight is not None

    for corr in insight.correlations:
        assert corr.metric_x is not None
        assert corr.metric_y is not None
        assert isinstance(corr.r, float)
        assert isinstance(corr.n, int)
        assert corr.strength in ["weak", "moderate", "strong", "none", "moderate (low data)", "weak (low data)", "none (low data)"]
        assert corr.direction in ["positive", "negative", "none"]


def test_metric_summary_wearable_no_data():
    """Test metric summary when no wearable data exists"""
    fake_repo = FakeInsightRepo()
    
    class EmptyWearableRepo:
        def list_for_user_in_range(self, *args, **kwargs):
            return []
    
    engine = InsightEngine(
        lab_repo=FakeLabRepo(),
        wearable_repo=EmptyWearableRepo(),
        health_data_repo=FakeHealthRepo(),
        symptom_repo=FakeSymptomRepo(),
        insight_repo=fake_repo,
    )
    
    summary = engine.summarise_wearable_metric(
        user_id=1,
        metric_name="hrv",
        unit="ms",
        window_days=30,
    )
    
    assert summary is None


def test_metric_summary_lab_no_data():
    """Test metric summary when no lab data exists"""
    fake_repo = FakeInsightRepo()
    
    class EmptyLabRepo:
        def list_for_user_in_range(self, *args, **kwargs):
            return []
    
    engine = InsightEngine(
        lab_repo=EmptyLabRepo(),
        wearable_repo=FakeWearableRepo(),
        health_data_repo=FakeHealthRepo(),
        symptom_repo=FakeSymptomRepo(),
        insight_repo=fake_repo,
    )
    
    summary = engine.summarise_lab_metric(
        user_id=1,
        test_name="glucose",
        window_days=30,
    )
    
    assert summary is None


def test_metric_summary_health_data_no_data():
    """Test metric summary when no health data exists"""
    fake_repo = FakeInsightRepo()
    
    class EmptyHealthRepo:
        def get_by_time_range(self, *args, **kwargs):
            return []
    
    engine = InsightEngine(
        lab_repo=FakeLabRepo(),
        wearable_repo=FakeWearableRepo(),
        health_data_repo=EmptyHealthRepo(),
        symptom_repo=FakeSymptomRepo(),
        insight_repo=fake_repo,
    )
    
    summary = engine.summarise_health_data_metric(
        user_id=1,
        data_type="stress_score",
        window_days=30,
    )
    
    assert summary is None


def test_trend_computation_improving():
    """Test trend computation for improving metric"""
    from app.engine.reasoning.insight_generator import _compute_trend
    from app.engine.analytics.time_series import DailyMetric
    from datetime import date
    
    # Improving trend: values decrease (e.g., symptom score going down)
    series = [
        DailyMetric(date=date(2024, 1, 1), value=100.0, count=1),
        DailyMetric(date=date(2024, 1, 2), value=90.0, count=1),
        DailyMetric(date=date(2024, 1, 3), value=80.0, count=1),
        DailyMetric(date=date(2024, 1, 4), value=70.0, count=1),
        DailyMetric(date=date(2024, 1, 5), value=60.0, count=1),
        DailyMetric(date=date(2024, 1, 6), value=50.0, count=1),
    ]
    
    trend, delta = _compute_trend(series)
    
    assert trend == "improving"
    assert delta < 0  # Negative delta means improvement


def test_trend_computation_worsening():
    """Test trend computation for worsening metric"""
    from app.engine.reasoning.insight_generator import _compute_trend
    from app.engine.analytics.time_series import DailyMetric
    from datetime import date
    
    # Worsening trend: values increase (e.g., symptom score going up)
    series = [
        DailyMetric(date=date(2024, 1, 1), value=50.0, count=1),
        DailyMetric(date=date(2024, 1, 2), value=60.0, count=1),
        DailyMetric(date=date(2024, 1, 3), value=70.0, count=1),
        DailyMetric(date=date(2024, 1, 4), value=80.0, count=1),
        DailyMetric(date=date(2024, 1, 5), value=90.0, count=1),
        DailyMetric(date=date(2024, 1, 6), value=100.0, count=1),
    ]
    
    trend, delta = _compute_trend(series)
    
    assert trend == "worsening"
    assert delta > 0  # Positive delta means worsening


def test_trend_computation_stable():
    """Test trend computation for stable metric"""
    from app.engine.reasoning.insight_generator import _compute_trend
    from app.engine.analytics.time_series import DailyMetric
    from datetime import date
    
    # Stable trend: values stay roughly the same
    series = [
        DailyMetric(date=date(2024, 1, 1), value=75.0, count=1),
        DailyMetric(date=date(2024, 1, 2), value=76.0, count=1),
        DailyMetric(date=date(2024, 1, 3), value=74.0, count=1),
        DailyMetric(date=date(2024, 1, 4), value=75.0, count=1),
        DailyMetric(date=date(2024, 1, 5), value=76.0, count=1),
        DailyMetric(date=date(2024, 1, 6), value=75.0, count=1),
    ]
    
    trend, delta = _compute_trend(series)
    
    assert trend == "stable"
    assert abs(delta) < 2.0  # Small change


def test_trend_computation_insufficient_data():
    """Test trend computation with insufficient data"""
    from app.engine.reasoning.insight_generator import _compute_trend
    from app.engine.analytics.time_series import DailyMetric
    from datetime import date
    
    # Less than 6 data points
    series = [
        DailyMetric(date=date(2024, 1, 1), value=75.0, count=1),
        DailyMetric(date=date(2024, 1, 2), value=80.0, count=1),
    ]
    
    trend, delta = _compute_trend(series)
    
    assert trend == "unknown"
    assert delta is None


def test_sleep_insight_no_sleep_data():
    """Test sleep insight generation when no sleep data exists"""
    fake_repo = FakeInsightRepo()
    
    class NoSleepWearableRepo:
        def list_for_user_in_range(self, user_id, start, end, metric_type=None):
            if metric_type == "sleep_duration":
                return []  # No sleep data
            # Return data for other metrics
            now = datetime.utcnow()
            data_points = []
            for i in range(5):
                obj = type("Obj", (), {})()
                obj.timestamp = now - timedelta(days=i)
                obj.value = 50.0
                data_points.append(obj)
            return data_points
    
    engine = InsightEngine(
        lab_repo=FakeLabRepo(),
        wearable_repo=NoSleepWearableRepo(),
        health_data_repo=FakeHealthRepo(),
        symptom_repo=FakeSymptomRepo(),
        insight_repo=fake_repo,
    )
    
    insight = engine.generate_sleep_insights(user_id=1, window_days=14)
    
    assert insight is None  # Should return None when no sleep data


def test_persist_insight_structure():
    """Test that persisted insight has correct structure"""
    fake_repo = FakeInsightRepo()
    
    engine = InsightEngine(
        lab_repo=FakeLabRepo(),
        wearable_repo=FakeWearableRepo(),
        health_data_repo=FakeHealthRepo(),
        symptom_repo=FakeSymptomRepo(),
        insight_repo=fake_repo,
    )
    
    insight = engine.generate_sleep_insights(user_id=1, window_days=14)
    assert insight is not None
    
    engine.persist_insight(insight)
    
    assert fake_repo.saved is not None
    assert fake_repo.saved["user_id"] == 1
    assert fake_repo.saved["insight_type"] == "sleep"
    assert fake_repo.saved["title"] == "Sleep pattern insights"
    assert "metadata_json" in fake_repo.saved
    
    import json
    metadata = json.loads(fake_repo.saved["metadata_json"])
    assert "metric_summaries" in metadata
    assert "correlations" in metadata
    assert "window_days" in metadata
    assert metadata["window_days"] == 14


def test_correlate_daily_metrics():
    """Test correlation computation between metrics"""
    from app.engine.analytics.time_series import DailyMetric
    from datetime import date
    
    fake_repo = FakeInsightRepo()
    
    engine = InsightEngine(
        lab_repo=FakeLabRepo(),
        wearable_repo=FakeWearableRepo(),
        health_data_repo=FakeHealthRepo(),
        symptom_repo=FakeSymptomRepo(),
        insight_repo=fake_repo,
    )
    
    # Create positively correlated series
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
    
    result = engine.correlate_daily_metrics(
        metric_x_name="metric_x",
        metric_y_name="metric_y",
        series_x=series_x,
        series_y=series_y,
    )
    
    assert result is not None
    assert result.metric_x == "metric_x"
    assert result.metric_y == "metric_y"
    assert result.r > 0  # Positive correlation
    assert result.direction == "positive"


def test_correlate_daily_metrics_insufficient_data():
    """Test correlation with insufficient overlapping data"""
    from app.engine.analytics.time_series import DailyMetric
    from datetime import date
    
    fake_repo = FakeInsightRepo()
    
    engine = InsightEngine(
        lab_repo=FakeLabRepo(),
        wearable_repo=FakeWearableRepo(),
        health_data_repo=FakeHealthRepo(),
        symptom_repo=FakeSymptomRepo(),
        insight_repo=fake_repo,
    )
    
    # Only one overlapping date
    series_x = [
        DailyMetric(date=date(2024, 1, 1), value=10.0, count=1),
    ]
    series_y = [
        DailyMetric(date=date(2024, 1, 1), value=5.0, count=1),
    ]
    
    result = engine.correlate_daily_metrics(
        metric_x_name="metric_x",
        metric_y_name="metric_y",
        series_x=series_x,
        series_y=series_y,
    )
    
    assert result is None  # Insufficient data (n < 3)
