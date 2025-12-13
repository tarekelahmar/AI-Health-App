"""Tests for insight quality validation"""
import pytest
from datetime import datetime, date, timedelta

from app.engine.reasoning.insight_generator import (
    GeneratedInsight,
    MetricSummary,
    CorrelationSummary,
)
from app.utils.insight_quality import (
    assess_insight_quality,
    validate_data_sufficiency,
    validate_statistical_validity,
    validate_trend_accuracy,
    validate_correlation_reliability,
    validate_medical_reasonableness,
    compare_insights,
    QualityReport,
)


class TestDataSufficiency:
    """Test data sufficiency validation"""
    
    def test_sufficient_data(self):
        """Test with sufficient data"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[
                MetricSummary(
                    metric_name="sleep_duration",
                    source="wearable",
                    window_days=30,
                    latest_value=7.5,
                    mean_value=7.2,
                    trend="stable",
                    trend_delta=0.1,
                )
            ],
            correlations=[
                CorrelationSummary(
                    metric_x="sleep_duration",
                    metric_y="hrv",
                    r=0.75,
                    n=20,
                    strength="strong",
                    direction="positive",
                    is_reliable=True,
                )
            ],
            window_days=30,
        )
        
        score, issues = validate_data_sufficiency(insight)
        
        assert score >= 0.8
        assert len(issues) == 0
    
    def test_insufficient_window(self):
        """Test with insufficient time window"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[
                MetricSummary(
                    metric_name="sleep_duration",
                    source="wearable",
                    window_days=7,
                    latest_value=7.5,
                    mean_value=7.2,
                    trend="stable",
                    trend_delta=0.1,
                )
            ],
            correlations=[],
            window_days=7,
        )
        
        score, issues = validate_data_sufficiency(insight)
        
        assert score < 1.0
        assert any("Window too short" in issue for issue in issues)
    
    def test_unreliable_correlations(self):
        """Test with unreliable correlations"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[
                MetricSummary(
                    metric_name="sleep_duration",
                    source="wearable",
                    window_days=30,
                    latest_value=7.5,
                    mean_value=7.2,
                    trend="stable",
                    trend_delta=0.1,
                )
            ],
            correlations=[
                CorrelationSummary(
                    metric_x="sleep_duration",
                    metric_y="hrv",
                    r=0.2,
                    n=5,
                    strength="weak (low data)",
                    direction="positive",
                    is_reliable=False,
                )
            ],
            window_days=30,
        )
        
        score, issues = validate_data_sufficiency(insight)
        
        assert score < 1.0
        assert any("insufficient data" in issue.lower() for issue in issues)
    
    def test_no_metric_summaries(self):
        """Test with no metric summaries"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[],
            correlations=[],
            window_days=30,
        )
        
        score, issues = validate_data_sufficiency(insight)
        
        assert score == 0.0
        assert any("No metric summaries" in issue for issue in issues)


class TestStatisticalValidity:
    """Test statistical validity validation"""
    
    def test_valid_statistics(self):
        """Test with valid statistics"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[
                MetricSummary(
                    metric_name="sleep_duration",
                    source="wearable",
                    window_days=30,
                    latest_value=7.5,
                    mean_value=7.2,
                    trend="stable",
                    trend_delta=0.1,
                )
            ],
            correlations=[
                CorrelationSummary(
                    metric_x="sleep_duration",
                    metric_y="hrv",
                    r=0.75,
                    n=20,
                    strength="strong",
                    direction="positive",
                    is_reliable=True,
                )
            ],
            window_days=30,
        )
        
        score, issues = validate_statistical_validity(insight)
        
        assert score >= 0.9
        assert len(issues) == 0
    
    def test_invalid_correlation_coefficient(self):
        """Test with invalid correlation coefficient"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[],
            correlations=[
                CorrelationSummary(
                    metric_x="sleep_duration",
                    metric_y="hrv",
                    r=1.5,  # Invalid: > 1.0
                    n=20,
                    strength="strong",
                    direction="positive",
                    is_reliable=True,
                )
            ],
            window_days=30,
        )
        
        score, issues = validate_statistical_validity(insight)
        
        assert score == 0.0
        assert any("Invalid correlation coefficient" in issue for issue in issues)
    
    def test_strength_mismatch(self):
        """Test when correlation strength doesn't match r value"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[],
            correlations=[
                CorrelationSummary(
                    metric_x="sleep_duration",
                    metric_y="hrv",
                    r=0.8,  # Strong correlation
                    n=20,
                    strength="weak",  # But marked as weak
                    direction="positive",
                    is_reliable=True,
                )
            ],
            window_days=30,
        )
        
        score, issues = validate_statistical_validity(insight)
        
        assert score < 1.0
        assert any("strength mismatch" in issue.lower() for issue in issues)


class TestTrendAccuracy:
    """Test trend accuracy validation"""
    
    def test_accurate_trends(self):
        """Test with accurate trends"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[
                MetricSummary(
                    metric_name="sleep_duration",
                    source="wearable",
                    window_days=30,
                    latest_value=7.5,
                    mean_value=7.2,
                    trend="stable",
                    trend_delta=0.1,  # Small delta = stable
                )
            ],
            correlations=[],
            window_days=30,
        )
        
        score, issues = validate_trend_accuracy(insight)
        
        assert score >= 0.9
        assert len(issues) == 0
    
    def test_invalid_trend_value(self):
        """Test with invalid trend value"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[
                MetricSummary(
                    metric_name="sleep_duration",
                    source="wearable",
                    window_days=30,
                    latest_value=7.5,
                    mean_value=7.2,
                    trend="invalid_trend",  # Invalid
                    trend_delta=0.1,
                )
            ],
            correlations=[],
            window_days=30,
        )
        
        score, issues = validate_trend_accuracy(insight)
        
        assert score < 1.0
        assert any("Invalid trend value" in issue for issue in issues)


class TestCorrelationReliability:
    """Test correlation reliability validation"""
    
    def test_reliable_correlations(self):
        """Test with reliable correlations"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[],
            correlations=[
                CorrelationSummary(
                    metric_x="sleep_duration",
                    metric_y="hrv",
                    r=0.75,
                    n=20,
                    strength="strong",
                    direction="positive",
                    is_reliable=True,  # Correctly marked as reliable
                )
            ],
            window_days=30,
        )
        
        score, issues = validate_correlation_reliability(insight)
        
        assert score >= 0.9
        assert len(issues) == 0
    
    def test_direction_mismatch(self):
        """Test when direction doesn't match correlation sign"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[],
            correlations=[
                CorrelationSummary(
                    metric_x="sleep_duration",
                    metric_y="hrv",
                    r=0.75,  # Positive
                    n=20,
                    strength="strong",
                    direction="negative",  # But marked as negative
                    is_reliable=True,
                )
            ],
            window_days=30,
        )
        
        score, issues = validate_correlation_reliability(insight)
        
        assert score < 1.0
        assert any("direction" in issue.lower() for issue in issues)


class TestMedicalReasonableness:
    """Test medical reasonableness validation"""
    
    def test_reasonable_values(self):
        """Test with medically reasonable values"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[
                MetricSummary(
                    metric_name="sleep_duration",
                    source="wearable",
                    window_days=30,
                    latest_value=7.5,  # Reasonable: 7.5 hours
                    mean_value=7.2,
                    trend="stable",
                    trend_delta=0.1,
                )
            ],
            correlations=[],
            window_days=30,
        )
        
        score, issues = validate_medical_reasonableness(insight)
        
        assert score >= 0.9
        assert len(issues) == 0
    
    def test_unreasonable_values(self):
        """Test with unreasonable values"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[
                MetricSummary(
                    metric_name="sleep_duration",
                    source="wearable",
                    window_days=30,
                    latest_value=25.0,  # Unreasonable: 25 hours
                    mean_value=7.2,
                    trend="stable",
                    trend_delta=0.1,
                )
            ],
            correlations=[],
            window_days=30,
        )
        
        score, issues = validate_medical_reasonableness(insight)
        
        assert score < 1.0
        assert any("outside reasonable range" in issue for issue in issues)


class TestAssessInsightQuality:
    """Test comprehensive quality assessment"""
    
    def test_high_quality_insight(self):
        """Test assessment of high-quality insight"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[
                MetricSummary(
                    metric_name="sleep_duration",
                    source="wearable",
                    window_days=30,
                    latest_value=7.5,
                    mean_value=7.2,
                    trend="stable",
                    trend_delta=0.1,
                )
            ],
            correlations=[
                CorrelationSummary(
                    metric_x="sleep_duration",
                    metric_y="hrv",
                    r=0.75,
                    n=20,
                    strength="strong",
                    direction="positive",
                    is_reliable=True,
                )
            ],
            window_days=30,
        )
        
        report = assess_insight_quality(insight)
        
        assert report.passed is True
        assert report.score.overall >= 0.7
        assert len(report.score.issues) == 0
    
    def test_low_quality_insight(self):
        """Test assessment of low-quality insight"""
        insight = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[],  # No metrics
            correlations=[],
            window_days=5,  # Too short
        )
        
        report = assess_insight_quality(insight)
        
        assert report.passed is False
        assert report.score.overall < 0.7
        assert len(report.score.issues) > 0
        assert len(report.recommendations) > 0


class TestCompareInsights:
    """Test insight comparison"""
    
    def test_consistent_insights(self):
        """Test comparing consistent insights"""
        insight1 = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[
                MetricSummary(
                    metric_name="sleep_duration",
                    source="wearable",
                    window_days=30,
                    latest_value=7.5,
                    mean_value=7.2,
                    trend="stable",
                    trend_delta=0.1,
                )
            ],
            correlations=[],
            window_days=30,
        )
        
        insight2 = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[
                MetricSummary(
                    metric_name="sleep_duration",
                    source="wearable",
                    window_days=30,
                    latest_value=7.6,  # Slightly different
                    mean_value=7.3,
                    trend="stable",
                    trend_delta=0.1,
                )
            ],
            correlations=[],
            window_days=30,
        )
        
        comparison = compare_insights(insight1, insight2)
        
        assert comparison["consistent"] is True
        assert len(comparison["differences"]) == 0
    
    def test_inconsistent_insights(self):
        """Test comparing inconsistent insights"""
        insight1 = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[
                MetricSummary(
                    metric_name="sleep_duration",
                    source="wearable",
                    window_days=30,
                    latest_value=7.5,
                    mean_value=7.2,
                    trend="improving",
                    trend_delta=-0.5,
                )
            ],
            correlations=[],
            window_days=30,
        )
        
        insight2 = GeneratedInsight(
            user_id=1,
            category="sleep",
            title="Sleep Insights",
            description="Test",
            metric_summaries=[
                MetricSummary(
                    metric_name="sleep_duration",
                    source="wearable",
                    window_days=30,
                    latest_value=7.5,
                    mean_value=7.2,
                    trend="worsening",  # Different trend
                    trend_delta=0.5,
                )
            ],
            correlations=[],
            window_days=30,
        )
        
        comparison = compare_insights(insight1, insight2)
        
        assert comparison["consistent"] is False
        assert len(comparison["metric_differences"]) > 0

