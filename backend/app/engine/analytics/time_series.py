"""Time series analysis utilities for health data.

This module converts lab / wearable / generic health data rows
into daily time-series suitable for analytics, rolling metrics, and correlation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Dict, Literal, Optional, Sequence

from app.domain.repositories.lab_result_repository import LabResultRepository
from app.domain.repositories.wearable_repository import WearableRepository
from app.domain.repositories.health_data_repository import HealthDataRepository

Aggregation = Literal["mean", "sum", "last"]


@dataclass
class MetricPoint:
    """Single timestamped numeric value."""

    timestamp: datetime
    value: float


@dataclass
class DailyMetric:
    """Aggregated daily value for a metric."""

    date: date
    value: float
    count: int


def _aggregate_by_day(
    points: Sequence[MetricPoint],
    aggregation: Aggregation = "mean",
) -> List[DailyMetric]:
    """Aggregate raw points into daily values."""
    buckets: Dict[date, List[float]] = {}

    for p in points:
        d = p.timestamp.date()
        buckets.setdefault(d, []).append(p.value)

    daily: List[DailyMetric] = []

    for d, values in buckets.items():
        if not values:
            continue

        if aggregation == "sum":
            agg = sum(values)
        elif aggregation == "last":
            # assume points are roughly time-ordered; last in list is latest
            agg = values[-1]
        else:  # "mean" (default)
            agg = sum(values) / len(values)

        daily.append(DailyMetric(date=d, value=agg, count=len(values)))

    # sort by date ascending
    daily.sort(key=lambda x: x.date)
    return daily


def build_wearable_daily_series(
    user_id: int,
    metric_type: str,
    start: datetime,
    end: datetime,
    wearable_repo: WearableRepository,
    aggregation: Aggregation = "mean",
) -> List[DailyMetric]:
    """Build a daily series for a wearable metric (e.g. 'sleep_duration', 'hrv')."""
    samples = wearable_repo.list_for_user_in_range(
        user_id=user_id,
        start=start,
        end=end,
        metric_type=metric_type,
    )

    points = [MetricPoint(timestamp=s.timestamp, value=s.value) for s in samples]
    return _aggregate_by_day(points, aggregation=aggregation)


def build_lab_daily_series(
    user_id: int,
    test_name: str,
    start: datetime,
    end: datetime,
    lab_repo: LabResultRepository,
    aggregation: Aggregation = "last",
) -> List[DailyMetric]:
    """Build a daily series from lab results (usually sparse; 'last' per day makes most sense)."""
    results = lab_repo.list_for_user_in_range(
        user_id=user_id,
        start=start,
        end=end,
        test_name=test_name,
    )

    points = [MetricPoint(timestamp=r.timestamp, value=r.value) for r in results]
    return _aggregate_by_day(points, aggregation=aggregation)


def build_health_data_daily_series(
    user_id: int,
    data_type: str,
    start: datetime,
    end: datetime,
    health_data_repo: HealthDataRepository,
    aggregation: Aggregation = "mean",
) -> List[DailyMetric]:
    """Build a daily series from generic HealthDataPoint records."""
    points_raw = health_data_repo.get_by_time_range(
        user_id=user_id,
        start_date=start,
        end_date=end,
        data_type=data_type,
    )

    points = [MetricPoint(timestamp=p.timestamp, value=p.value) for p in points_raw]
    return _aggregate_by_day(points, aggregation=aggregation)


def merge_daily_series(
    series_list: Sequence[List[DailyMetric]],
    aggregation: Aggregation = "mean",
) -> List[DailyMetric]:
    """
    Merge multiple daily series into one, re-aggregating values for matching dates.

    Useful if you want to combine, for example:
    - health_data "sleep_duration"
    - wearable "sleep_duration"
    into a single daily sleep metric.
    """
    value_buckets: Dict[date, List[float]] = {}

    for series in series_list:
        for item in series:
            value_buckets.setdefault(item.date, []).append(item.value)

    merged_points = [
        MetricPoint(timestamp=datetime.combine(d, datetime.min.time()), value=sum(vals) / len(vals))
        for d, vals in value_buckets.items()
    ]

    return _aggregate_by_day(merged_points, aggregation=aggregation)


def to_dict_series(series: Sequence[DailyMetric]) -> List[Dict[str, float]]:
    """
    Utility to convert DailyMetric objects into plain dicts
    suitable for JSON responses or feeding into the LLM context.
    """
    return [
        {
            "date": dm.date.isoformat(),
            "value": dm.value,
            "count": dm.count,
        }
        for dm in series
    ]
