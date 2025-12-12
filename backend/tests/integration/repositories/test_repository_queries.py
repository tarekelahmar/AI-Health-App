"""Comprehensive tests for repository query methods"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.domain.repositories.wearable_repository import WearableRepository
from app.domain.repositories.lab_result_repository import LabResultRepository
from app.domain.repositories.health_data_repository import HealthDataRepository
from app.domain.models.wearable_sample import WearableSample
from app.domain.models.lab_result import LabResult
from app.domain.models.health_data_point import HealthDataPoint


class TestWearableRepositoryQueries:
    """Test WearableRepository query methods"""
    
    def test_list_for_user_in_range_with_metric_filter(self, db):
        """Test querying wearable data with metric type filter"""
        repo = WearableRepository(db)
        
        # Create test data
        now = datetime.utcnow()
        repo.create(
            user_id=1,
            device_type="fitbit",
            metric_type="hrv",
            value=70.0,
            unit="ms",
            timestamp=now - timedelta(days=1),
        )
        repo.create(
            user_id=1,
            device_type="fitbit",
            metric_type="sleep_duration",
            value=7.5,
            unit="hours",
            timestamp=now - timedelta(days=1),
        )
        repo.create(
            user_id=1,
            device_type="fitbit",
            metric_type="hrv",
            value=75.0,
            unit="ms",
            timestamp=now - timedelta(days=2),
        )
        
        # Query with metric filter
        start = now - timedelta(days=3)
        end = now
        results = repo.list_for_user_in_range(
            user_id=1,
            start=start,
            end=end,
            metric_type="hrv",
        )
        
        assert len(results) == 2
        assert all(r.metric_type == "hrv" for r in results)
        assert results[0].value == 75.0  # Older first (ascending)
        assert results[1].value == 70.0
    
    def test_list_for_user_in_range_no_metric_filter(self, db: Session):
        """Test querying all metrics without filter"""
        repo = WearableRepository(db)
        
        now = datetime.utcnow()
        repo.create(user_id=1, device_type="fitbit", metric_type="hrv", value=70.0, unit="ms", timestamp=now - timedelta(days=1))
        repo.create(user_id=1, device_type="fitbit", metric_type="sleep", value=7.5, unit="hours", timestamp=now - timedelta(days=1))
        
        results = repo.list_for_user_in_range(
            user_id=1,
            start=now - timedelta(days=3),
            end=now,
        )
        
        assert len(results) == 2
    
    def test_list_for_user_in_range_time_boundaries(self, db: Session):
        """Test that time boundaries are respected"""
        repo = WearableRepository(db)
        
        now = datetime.utcnow()
        # Create data outside range
        repo.create(user_id=1, device_type="fitbit", metric_type="hrv", value=50.0, unit="ms", timestamp=now - timedelta(days=10))
        # Create data inside range
        repo.create(user_id=1, device_type="fitbit", metric_type="hrv", value=70.0, unit="ms", timestamp=now - timedelta(days=1))
        # Create data outside range
        repo.create(user_id=1, device_type="fitbit", metric_type="hrv", value=80.0, unit="ms", timestamp=now + timedelta(days=1))
        
        results = repo.list_for_user_in_range(
            user_id=1,
            start=now - timedelta(days=3),
            end=now,
        )
        
        assert len(results) == 1
        assert results[0].value == 70.0
    
    def test_get_latest_value(self, db: Session):
        """Test getting latest value for a metric"""
        repo = WearableRepository(db)
        
        now = datetime.utcnow()
        repo.create(user_id=1, device_type="fitbit", metric_type="hrv", value=70.0, unit="ms", timestamp=now - timedelta(days=2))
        repo.create(user_id=1, device_type="fitbit", metric_type="hrv", value=75.0, unit="ms", timestamp=now - timedelta(days=1))
        
        latest = repo.get_latest_value(user_id=1, metric_type="hrv")
        
        assert latest is not None
        assert latest.value == 75.0
        assert latest.metric_type == "hrv"
    
    def test_get_latest_value_no_data(self, db: Session):
        """Test getting latest value when no data exists"""
        repo = WearableRepository(db)
        
        latest = repo.get_latest_value(user_id=999, metric_type="hrv")
        
        assert latest is None


class TestLabResultRepositoryQueries:
    """Test LabResultRepository query methods"""
    
    def test_list_for_user_in_range_with_test_filter(self, db: Session):
        """Test querying lab results with test name filter"""
        repo = LabResultRepository(db)
        
        now = datetime.utcnow()
        repo.create(user_id=1, test_name="glucose", value=100.0, unit="mg/dL", timestamp=now - timedelta(days=1))
        repo.create(user_id=1, test_name="cholesterol", value=200.0, unit="mg/dL", timestamp=now - timedelta(days=1))
        repo.create(user_id=1, test_name="glucose", value=110.0, unit="mg/dL", timestamp=now - timedelta(days=2))
        
        results = repo.list_for_user_in_range(
            user_id=1,
            start=now - timedelta(days=3),
            end=now,
            test_name="glucose",
        )
        
        assert len(results) == 2
        assert all(r.test_name == "glucose" for r in results)
        assert results[0].value == 110.0  # Older first
        assert results[1].value == 100.0
    
    def test_get_latest_for_test(self, db: Session):
        """Test getting latest result for a specific test"""
        repo = LabResultRepository(db)
        
        now = datetime.utcnow()
        repo.create(user_id=1, test_name="glucose", value=100.0, unit="mg/dL", timestamp=now - timedelta(days=2))
        repo.create(user_id=1, test_name="glucose", value=110.0, unit="mg/dL", timestamp=now - timedelta(days=1))
        
        latest = repo.get_latest_for_test(user_id=1, test_name="glucose")
        
        assert latest is not None
        assert latest.value == 110.0
        assert latest.test_name == "glucose"
    
    def test_list_for_user_pagination(self, db: Session):
        """Test pagination in list_for_user"""
        repo = LabResultRepository(db)
        
        now = datetime.utcnow()
        # Create 5 results
        for i in range(5):
            repo.create(
                user_id=1,
                test_name="glucose",
                value=100.0 + i,
                unit="mg/dL",
                timestamp=now - timedelta(days=i),
            )
        
        # Get first 2
        results = repo.list_for_user(user_id=1, limit=2, offset=0)
        assert len(results) == 2
        assert results[0].value == 104.0  # Most recent first (desc order)
        
        # Get next 2
        results = repo.list_for_user(user_id=1, limit=2, offset=2)
        assert len(results) == 2


class TestHealthDataRepositoryQueries:
    """Test HealthDataRepository query methods"""
    
    def test_get_by_time_range_with_filters(self, db: Session):
        """Test querying health data with type and source filters"""
        repo = HealthDataRepository(db)
        
        now = datetime.utcnow()
        repo.create(user_id=1, data_type="stress_score", value=5.0, unit="score", source="manual", timestamp=now - timedelta(days=1))
        repo.create(user_id=1, data_type="stress_score", value=6.0, unit="score", source="app", timestamp=now - timedelta(days=1))
        repo.create(user_id=1, data_type="mood", value=7.0, unit="score", source="manual", timestamp=now - timedelta(days=1))
        
        results = repo.get_by_time_range(
            user_id=1,
            start_date=now - timedelta(days=3),
            end_date=now,
            data_type="stress_score",
            source="manual",
        )
        
        assert len(results) == 1
        assert results[0].data_type == "stress_score"
        assert results[0].source == "manual"
        assert results[0].value == 5.0
    
    def test_get_latest(self, db: Session):
        """Test getting latest health data point"""
        repo = HealthDataRepository(db)
        
        now = datetime.utcnow()
        repo.create(user_id=1, data_type="stress_score", value=5.0, unit="score", source="manual", timestamp=now - timedelta(days=2))
        repo.create(user_id=1, data_type="stress_score", value=6.0, unit="score", source="manual", timestamp=now - timedelta(days=1))
        
        latest = repo.get_latest(user_id=1, data_type="stress_score")
        
        assert latest is not None
        assert latest.value == 6.0
    
    def test_get_recent(self, db: Session):
        """Test getting recent data within N days"""
        repo = HealthDataRepository(db)
        
        now = datetime.utcnow()
        # Old data (outside 30 days)
        repo.create(user_id=1, data_type="stress_score", value=5.0, unit="score", source="manual", timestamp=now - timedelta(days=40))
        # Recent data (within 30 days)
        repo.create(user_id=1, data_type="stress_score", value=6.0, unit="score", source="manual", timestamp=now - timedelta(days=10))
        
        results = repo.get_recent(user_id=1, days=30, data_type="stress_score")
        
        assert len(results) == 1
        assert results[0].value == 6.0
    
    def test_get_average(self, db: Session):
        """Test calculating average value"""
        repo = HealthDataRepository(db)
        
        now = datetime.utcnow()
        repo.create(user_id=1, data_type="stress_score", value=5.0, unit="score", source="manual", timestamp=now - timedelta(days=1))
        repo.create(user_id=1, data_type="stress_score", value=7.0, unit="score", source="manual", timestamp=now - timedelta(days=2))
        repo.create(user_id=1, data_type="stress_score", value=6.0, unit="score", source="manual", timestamp=now - timedelta(days=3))
        
        avg = repo.get_average(user_id=1, data_type="stress_score", days=30)
        
        assert avg is not None
        assert abs(avg - 6.0) < 0.01  # (5 + 7 + 6) / 3 = 6
    
    def test_get_trend(self, db: Session):
        """Test trend calculation"""
        repo = HealthDataRepository(db)
        
        now = datetime.utcnow()
        # Improving trend (values decreasing)
        repo.create(user_id=1, data_type="stress_score", value=10.0, unit="score", source="manual", timestamp=now - timedelta(days=5))
        repo.create(user_id=1, data_type="stress_score", value=8.0, unit="score", source="manual", timestamp=now - timedelta(days=4))
        repo.create(user_id=1, data_type="stress_score", value=6.0, unit="score", source="manual", timestamp=now - timedelta(days=3))
        repo.create(user_id=1, data_type="stress_score", value=4.0, unit="score", source="manual", timestamp=now - timedelta(days=2))
        repo.create(user_id=1, data_type="stress_score", value=2.0, unit="score", source="manual", timestamp=now - timedelta(days=1))
        
        trend = repo.get_trend(user_id=1, data_type="stress_score", days=30)
        
        assert trend["trend"] == "improving"
        assert trend["slope"] < 0  # Negative slope = improving
        assert trend["confidence"] > 0
    
    def test_get_trend_insufficient_data(self, db: Session):
        """Test trend with insufficient data"""
        repo = HealthDataRepository(db)
        
        now = datetime.utcnow()
        repo.create(user_id=1, data_type="stress_score", value=5.0, unit="score", source="manual", timestamp=now - timedelta(days=1))
        
        trend = repo.get_trend(user_id=1, data_type="stress_score", days=30)
        
        assert trend["trend"] == "insufficient_data"
        assert trend["confidence"] == 0.0
    
    def test_list_for_user_in_range_alias(self, db: Session):
        """Test list_for_user_in_range alias method"""
        repo = HealthDataRepository(db)
        
        now = datetime.utcnow()
        repo.create(user_id=1, data_type="stress_score", value=5.0, unit="score", source="manual", timestamp=now - timedelta(days=1))
        
        results = repo.list_for_user_in_range(
            user_id=1,
            data_type="stress_score",
            start=now - timedelta(days=3),
            end=now,
        )
        
        assert len(results) == 1
        assert results[0].data_type == "stress_score"

