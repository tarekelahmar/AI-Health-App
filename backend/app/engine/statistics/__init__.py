"""
Statistical methods for robust health data analysis.

Phase 2.1: Robust estimators for baselines and change detection.
"""

from app.engine.statistics.baseline import (
    RobustBaseline,
    BaselineEstimate,
    compute_robust_baseline,
    median_absolute_deviation,
)

__all__ = [
    "RobustBaseline",
    "BaselineEstimate",
    "compute_robust_baseline",
    "median_absolute_deviation",
]
