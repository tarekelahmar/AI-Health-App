"""Insight quality validation and testing utilities"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.engine.reasoning.insight_generator import GeneratedInsight, MetricSummary, CorrelationSummary
from app.engine.analytics.time_series import DailyMetric


@dataclass
class QualityScore:
    """Quality score for an insight"""
    overall: float  # 0.0 to 1.0
    data_sufficiency: float
    statistical_validity: float
    trend_accuracy: float
    correlation_reliability: float
    issues: List[str]  # List of quality issues found


@dataclass
class QualityReport:
    """Complete quality report for an insight"""
    insight: GeneratedInsight
    score: QualityScore
    recommendations: List[str]
    passed: bool  # True if quality is acceptable


def validate_data_sufficiency(insight: GeneratedInsight) -> Tuple[float, List[str]]:
    """
    Validate that there's sufficient data to generate reliable insights.
    
    Returns:
        (score, issues) where score is 0.0-1.0 and issues is list of problems
    """
    issues = []
    score = 1.0
    
    # Check minimum data points for each metric
    min_data_points = 10  # Minimum for reliable trends
    min_window_days = 14  # Minimum window for meaningful insights
    
    if insight.window_days < min_window_days:
        issues.append(f"Window too short: {insight.window_days} days (minimum: {min_window_days})")
        score -= 0.3
    
    # Check metric summaries have sufficient data
    for metric in insight.metric_summaries:
        if metric.latest_value is None:
            issues.append(f"Metric {metric.metric_name} has no latest value")
            score -= 0.2
        if metric.mean_value is None:
            issues.append(f"Metric {metric.metric_name} has no mean value")
            score -= 0.2
    
    # Check correlations have sufficient data points
    for corr in insight.correlations:
        if corr.n < 10:
            issues.append(
                f"Correlation {corr.metric_x}-{corr.metric_y} has insufficient data (n={corr.n})"
            )
            score -= 0.15
        if not corr.is_reliable:
            issues.append(
                f"Correlation {corr.metric_x}-{corr.metric_y} is not reliable (r={corr.r:.2f}, n={corr.n})"
            )
            score -= 0.1
    
    # Ensure we have at least one metric summary
    if len(insight.metric_summaries) == 0:
        issues.append("No metric summaries available")
        score = 0.0
    
    return max(0.0, score), issues


def validate_statistical_validity(insight: GeneratedInsight) -> Tuple[float, List[str]]:
    """
    Validate statistical validity of insights.
    
    Returns:
        (score, issues)
    """
    issues = []
    score = 1.0
    
    # Check correlations are statistically sound
    for corr in insight.correlations:
        # Check correlation coefficient is in valid range
        if abs(corr.r) > 1.0:
            issues.append(f"Invalid correlation coefficient: {corr.r}")
            score = 0.0
        
        # Check sample size is adequate
        if corr.n < 3:
            issues.append(f"Correlation {corr.metric_x}-{corr.metric_y} has too few data points (n={corr.n})")
            score -= 0.3
        
        # Check strength interpretation matches correlation
        abs_r = abs(corr.r)
        if abs_r >= 0.7 and "strong" not in corr.strength.lower():
            issues.append(f"Correlation strength mismatch: r={corr.r:.2f} but strength={corr.strength}")
            score -= 0.1
        elif abs_r < 0.3 and "none" not in corr.strength.lower() and "weak" not in corr.strength.lower():
            issues.append(f"Correlation strength mismatch: r={corr.r:.2f} but strength={corr.strength}")
            score -= 0.1
    
    # Check metric values are reasonable (not NaN, not infinite)
    for metric in insight.metric_summaries:
        if metric.latest_value is not None:
            if not (-1e6 < metric.latest_value < 1e6):
                issues.append(f"Metric {metric.metric_name} has unreasonable value: {metric.latest_value}")
                score -= 0.2
        if metric.mean_value is not None:
            if not (-1e6 < metric.mean_value < 1e6):
                issues.append(f"Metric {metric.metric_name} has unreasonable mean: {metric.mean_value}")
                score -= 0.2
    
    return max(0.0, score), issues


def validate_trend_accuracy(insight: GeneratedInsight) -> Tuple[float, List[str]]:
    """
    Validate that trends are accurately computed.
    
    Returns:
        (score, issues)
    """
    issues = []
    score = 1.0
    
    for metric in insight.metric_summaries:
        # Check trend direction matches trend_delta
        if metric.trend_delta is not None:
            if metric.trend == "improving" and metric.trend_delta > 0:
                # For metrics where lower is better (e.g., symptoms), improving means negative delta
                # For metrics where higher is better (e.g., sleep), improving means positive delta
                # This depends on the metric type - we'll flag it for review
                issues.append(
                    f"Metric {metric.metric_name}: trend='improving' but delta={metric.trend_delta:.2f} > 0"
                )
                score -= 0.1
            elif metric.trend == "worsening" and metric.trend_delta < 0:
                issues.append(
                    f"Metric {metric.metric_name}: trend='worsening' but delta={metric.trend_delta:.2f} < 0"
                )
                score -= 0.1
            elif metric.trend == "stable" and abs(metric.trend_delta) > 10:
                # If delta is large, trend shouldn't be stable
                issues.append(
                    f"Metric {metric.metric_name}: trend='stable' but large delta={metric.trend_delta:.2f}"
                )
                score -= 0.1
        
        # Check trend is one of valid values
        valid_trends = ["improving", "worsening", "stable", "unknown"]
        if metric.trend not in valid_trends:
            issues.append(f"Invalid trend value: {metric.trend}")
            score -= 0.2
    
    return max(0.0, score), issues


def validate_correlation_reliability(insight: GeneratedInsight) -> Tuple[float, List[str]]:
    """
    Validate that correlations are reliable and meaningful.
    
    Returns:
        (score, issues)
    """
    issues = []
    score = 1.0
    
    for corr in insight.correlations:
        # Check reliability flag matches actual reliability
        expected_reliable = corr.n >= 10 and abs(corr.r) >= 0.3
        if corr.is_reliable != expected_reliable:
            issues.append(
                f"Correlation {corr.metric_x}-{corr.metric_y}: "
                f"is_reliable={corr.is_reliable} but should be {expected_reliable}"
            )
            score -= 0.2
        
        # Check direction matches correlation sign
        if corr.r > 0 and corr.direction != "positive":
            issues.append(f"Correlation {corr.metric_x}-{corr.metric_y}: r>0 but direction={corr.direction}")
            score -= 0.1
        elif corr.r < 0 and corr.direction != "negative":
            issues.append(f"Correlation {corr.metric_x}-{corr.metric_y}: r<0 but direction={corr.direction}")
            score -= 0.1
        elif corr.r == 0 and corr.direction != "none":
            issues.append(f"Correlation {corr.metric_x}-{corr.metric_y}: r=0 but direction={corr.direction}")
            score -= 0.1
    
    return max(0.0, score), issues


def validate_medical_reasonableness(insight: GeneratedInsight) -> Tuple[float, List[str]]:
    """
    Validate that insight values are medically reasonable.
    
    This is a basic sanity check - more sophisticated validation would require
    domain knowledge and reference ranges.
    
    Returns:
        (score, issues)
    """
    issues = []
    score = 1.0
    
    # Define reasonable ranges for common metrics
    reasonable_ranges = {
        "sleep_duration": (3.0, 12.0),  # hours
        "hrv": (20.0, 200.0),  # ms
        "activity_minutes": (0.0, 600.0),  # minutes per day
        "stress_score": (0.0, 10.0),  # 0-10 scale
    }
    
    for metric in insight.metric_summaries:
        metric_name = metric.metric_name.lower()
        
        # Check if we have a reasonable range for this metric
        for key, (min_val, max_val) in reasonable_ranges.items():
            if key in metric_name:
                if metric.latest_value is not None:
                    if not (min_val <= metric.latest_value <= max_val):
                        issues.append(
                            f"Metric {metric.metric_name} value {metric.latest_value} "
                            f"outside reasonable range [{min_val}, {max_val}]"
                        )
                        score -= 0.15
                if metric.mean_value is not None:
                    if not (min_val <= metric.mean_value <= max_val):
                        issues.append(
                            f"Metric {metric.metric_name} mean {metric.mean_value} "
                            f"outside reasonable range [{min_val}, {max_val}]"
                        )
                        score -= 0.15
                break
    
    return max(0.0, score), issues


def assess_insight_quality(insight: GeneratedInsight) -> QualityReport:
    """
    Comprehensive quality assessment of an insight.
    
    Args:
        insight: The GeneratedInsight to assess
        
    Returns:
        QualityReport with scores, issues, and recommendations
    """
    all_issues = []
    
    # Assess each quality dimension
    data_score, data_issues = validate_data_sufficiency(insight)
    all_issues.extend(data_issues)
    
    stat_score, stat_issues = validate_statistical_validity(insight)
    all_issues.extend(stat_issues)
    
    trend_score, trend_issues = validate_trend_accuracy(insight)
    all_issues.extend(trend_issues)
    
    corr_score, corr_issues = validate_correlation_reliability(insight)
    all_issues.extend(corr_issues)
    
    medical_score, medical_issues = validate_medical_reasonableness(insight)
    all_issues.extend(medical_issues)
    
    # Calculate overall score (weighted average)
    overall_score = (
        data_score * 0.3 +  # Data sufficiency is most important
        stat_score * 0.25 +
        trend_score * 0.2 +
        corr_score * 0.15 +
        medical_score * 0.1
    )
    
    quality_score = QualityScore(
        overall=overall_score,
        data_sufficiency=data_score,
        statistical_validity=stat_score,
        trend_accuracy=trend_score,
        correlation_reliability=corr_score,
        issues=all_issues,
    )
    
    # Generate recommendations
    recommendations = []
    if overall_score < 0.7:
        recommendations.append("Insight quality is below acceptable threshold (0.7)")
    if data_score < 0.7:
        recommendations.append("Collect more data points for more reliable insights")
    if stat_score < 0.8:
        recommendations.append("Review statistical calculations for accuracy")
    if len([c for c in insight.correlations if not c.is_reliable]) > 0:
        recommendations.append("Some correlations are not reliable - consider excluding them")
    if len(all_issues) == 0:
        recommendations.append("Insight quality is excellent - no issues found")
    
    return QualityReport(
        insight=insight,
        score=quality_score,
        recommendations=recommendations,
        passed=overall_score >= 0.7,  # Pass if overall score >= 0.7
    )


def compare_insights(insight1: GeneratedInsight, insight2: GeneratedInsight) -> Dict[str, Any]:
    """
    Compare two insights to check for consistency.
    
    Useful for testing that the same data produces similar insights.
    
    Returns:
        Dictionary with comparison results
    """
    comparison = {
        "consistent": True,
        "differences": [],
        "metric_differences": [],
        "correlation_differences": [],
    }
    
    # Compare metric summaries
    metric_names_1 = {m.metric_name for m in insight1.metric_summaries}
    metric_names_2 = {m.metric_name for m in insight2.metric_summaries}
    
    if metric_names_1 != metric_names_2:
        comparison["consistent"] = False
        comparison["differences"].append(
            f"Different metrics: {metric_names_1} vs {metric_names_2}"
        )
    
    # Compare trends for common metrics
    for metric1 in insight1.metric_summaries:
        metric2 = next(
            (m for m in insight2.metric_summaries if m.metric_name == metric1.metric_name),
            None
        )
        if metric2:
            if metric1.trend != metric2.trend:
                comparison["consistent"] = False
                comparison["metric_differences"].append(
                    f"{metric1.metric_name}: trend changed from {metric1.trend} to {metric2.trend}"
                )
            
            # Check if values are similar (within 10%)
            if metric1.mean_value and metric2.mean_value:
                diff_pct = abs(metric1.mean_value - metric2.mean_value) / metric1.mean_value * 100
                if diff_pct > 10:
                    comparison["metric_differences"].append(
                        f"{metric1.metric_name}: mean value differs by {diff_pct:.1f}%"
                    )
    
    # Compare correlations
    corr_pairs_1 = {(c.metric_x, c.metric_y) for c in insight1.correlations}
    corr_pairs_2 = {(c.metric_x, c.metric_y) for c in insight2.correlations}
    
    if corr_pairs_1 != corr_pairs_2:
        comparison["consistent"] = False
        comparison["correlation_differences"].append(
            f"Different correlation pairs: {corr_pairs_1} vs {corr_pairs_2}"
        )
    
    return comparison

