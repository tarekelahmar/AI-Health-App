"""Integration tests for insight quality with real data"""
import pytest
from datetime import datetime, timedelta

from app.domain.repositories import (
    WearableRepository,
    LabResultRepository,
    HealthDataRepository,
    SymptomRepository,
    InsightRepository,
)
from app.engine.reasoning.insight_generator import InsightEngine
from app.utils.insight_quality import assess_insight_quality, compare_insights


class TestInsightQualityIntegration:
    """Integration tests for insight quality with real repositories"""
    
    def test_quality_with_real_data(self, db):
        """Test insight quality with realistic data"""
        # Create repositories
        wearable_repo = WearableRepository(db)
        lab_repo = LabResultRepository(db)
        health_repo = HealthDataRepository(db)
        symptom_repo = SymptomRepository(db)
        insight_repo = InsightRepository(db)
        
        # Create engine
        engine = InsightEngine(
            lab_repo=lab_repo,
            wearable_repo=wearable_repo,
            health_data_repo=health_repo,
            symptom_repo=symptom_repo,
            insight_repo=insight_repo,
        )
        
        # Create realistic wearable data (30 days)
        now = datetime.utcnow()
        for i in range(30):
            timestamp = now - timedelta(days=i)
            # Sleep duration: 7-8 hours with slight variation
            wearable_repo.create(
                user_id=1,
                device_type="fitbit",
                metric_type="sleep_duration",
                value=7.0 + (i % 3) * 0.3,  # 7.0 to 7.9 hours
                unit="hours",
                timestamp=timestamp,
            )
            # HRV: 50-80ms with correlation to sleep
            wearable_repo.create(
                user_id=1,
                device_type="fitbit",
                metric_type="hrv",
                value=50 + (i % 3) * 10,  # 50 to 80ms
                unit="ms",
                timestamp=timestamp,
            )
        
        # Generate insight
        insight = engine.generate_sleep_insights(user_id=1, window_days=30)
        
        assert insight is not None
        
        # Assess quality
        report = assess_insight_quality(insight)
        
        # Should pass quality checks with realistic data
        assert report.passed is True
        assert report.score.overall >= 0.7
        assert report.score.data_sufficiency >= 0.7
        assert report.score.statistical_validity >= 0.8
    
    def test_quality_with_insufficient_data(self, db):
        """Test quality assessment with insufficient data"""
        wearable_repo = WearableRepository(db)
        lab_repo = LabResultRepository(db)
        health_repo = HealthDataRepository(db)
        symptom_repo = SymptomRepository(db)
        insight_repo = InsightRepository(db)
        
        engine = InsightEngine(
            lab_repo=lab_repo,
            wearable_repo=wearable_repo,
            health_data_repo=health_repo,
            symptom_repo=symptom_repo,
            insight_repo=insight_repo,
        )
        
        # Create only 3 days of data (insufficient)
        now = datetime.utcnow()
        for i in range(3):
            timestamp = now - timedelta(days=i)
            wearable_repo.create(
                user_id=1,
                device_type="fitbit",
                metric_type="sleep_duration",
                value=7.0,
                unit="hours",
                timestamp=timestamp,
            )
        
        # Generate insight
        insight = engine.generate_sleep_insights(user_id=1, window_days=30)
        
        if insight:
            report = assess_insight_quality(insight)
            # Should fail or have low quality score
            assert report.score.data_sufficiency < 0.7 or not report.passed
    
    def test_consistency_across_runs(self, db):
        """Test that same data produces consistent insights"""
        wearable_repo = WearableRepository(db)
        lab_repo = LabResultRepository(db)
        health_repo = HealthDataRepository(db)
        symptom_repo = SymptomRepository(db)
        insight_repo = InsightRepository(db)
        
        engine = InsightEngine(
            lab_repo=lab_repo,
            wearable_repo=wearable_repo,
            health_data_repo=health_repo,
            symptom_repo=symptom_repo,
            insight_repo=insight_repo,
        )
        
        # Create consistent data
        now = datetime.utcnow()
        for i in range(30):
            timestamp = now - timedelta(days=i)
            wearable_repo.create(
                user_id=1,
                device_type="fitbit",
                metric_type="sleep_duration",
                value=7.5,
                unit="hours",
                timestamp=timestamp,
            )
            wearable_repo.create(
                user_id=1,
                device_type="fitbit",
                metric_type="hrv",
                value=70.0,
                unit="ms",
                timestamp=timestamp,
            )
        
        # Generate insights twice
        insight1 = engine.generate_sleep_insights(user_id=1, window_days=30)
        insight2 = engine.generate_sleep_insights(user_id=1, window_days=30)
        
        assert insight1 is not None
        assert insight2 is not None
        
        # Compare insights
        comparison = compare_insights(insight1, insight2)
        
        # Should be consistent (same data = same insights)
        assert comparison["consistent"] is True
        assert len(comparison["differences"]) == 0

