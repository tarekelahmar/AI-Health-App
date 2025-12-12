"""Analytics layer - time series, rolling metrics, and correlation analysis"""

from .time_series import (
    DailyMetric,
    MetricPoint,
    build_wearable_daily_series,
    build_lab_daily_series,
    build_health_data_daily_series,
    merge_daily_series,
    to_dict_series,
)

from .rolling_metrics import (
    RollingStat,
    compute_rolling_stats,
    to_dict_series as rolling_to_dict_series,
)

from .correlation import (
    CorrelationResult,
    compute_metric_correlation,
    to_dict as correlation_to_dict,
)

__all__ = [
    # Time series
    "DailyMetric",
    "MetricPoint",
    "build_wearable_daily_series",
    "build_lab_daily_series",
    "build_health_data_daily_series",
    "merge_daily_series",
    "to_dict_series",
    # Rolling metrics
    "RollingStat",
    "compute_rolling_stats",
    "rolling_to_dict_series",
    # Correlation
    "CorrelationResult",
    "compute_metric_correlation",
    "correlation_to_dict",
]

