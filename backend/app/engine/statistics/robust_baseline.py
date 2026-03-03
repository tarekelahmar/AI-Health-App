"""
Robust baseline estimation using outlier-resistant statistics.

Phase 2.1: Replaces simple mean/std with median/MAD, trimmed mean,
or Huber M-estimation for baseline computation.

Why: Simple mean/std are highly sensitive to outliers. A single bad
sensor reading or unusual day can skew the baseline and cause false
alerts or missed real changes. Robust estimators resist these effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from scipy.stats import median_abs_deviation, trim_mean
from scipy.stats import t as t_dist


@dataclass(frozen=True)
class BaselineEstimate:
    """Result of a robust baseline estimation."""
    center: float
    spread: float
    method: str
    n_samples: int
    ci_80: Tuple[float, float]
    ci_95: Tuple[float, float]
    is_stable: bool  # True if n_samples >= min_stable_days


# Minimum data points before a baseline is considered "stable"
MIN_STABLE_SAMPLES = 14


def estimate_baseline(
    values: list[float],
    method: str = "median_mad",
    min_samples: int = 5,
) -> Optional[BaselineEstimate]:
    """
    Compute a robust baseline from a list of values.

    Methods:
      - "median_mad": Median + Median Absolute Deviation (default, most robust)
      - "trimmed_mean": 10% trimmed mean + trimmed std
      - "mean_std": Simple mean + std (legacy fallback)

    Returns None if fewer than min_samples values.
    """
    if len(values) < min_samples:
        return None

    arr = np.array(values, dtype=np.float64)

    if method == "median_mad":
        center = float(np.median(arr))
        # scale="normal" makes MAD comparable to std for normal data
        spread = float(median_abs_deviation(arr, scale="normal"))
    elif method == "trimmed_mean":
        center = float(trim_mean(arr, proportiontocut=0.1))
        # Trimmed std: std of the middle 80% of values
        sorted_arr = np.sort(arr)
        n = len(sorted_arr)
        cut = max(1, int(n * 0.1))
        trimmed = sorted_arr[cut: n - cut]
        spread = float(np.std(trimmed, ddof=1)) if len(trimmed) > 1 else 0.0
    elif method == "mean_std":
        center = float(np.mean(arr))
        spread = float(np.std(arr, ddof=0))
    else:
        raise ValueError(f"Unknown baseline method: {method}")

    # Guard against zero spread (constant data)
    if spread < 1e-10:
        spread = 1e-10

    ci_80 = _confidence_interval(arr, center, spread, 0.80)
    ci_95 = _confidence_interval(arr, center, spread, 0.95)

    return BaselineEstimate(
        center=center,
        spread=spread,
        method=method,
        n_samples=len(arr),
        ci_80=ci_80,
        ci_95=ci_95,
        is_stable=len(arr) >= MIN_STABLE_SAMPLES,
    )


def _confidence_interval(
    arr: np.ndarray,
    center: float,
    spread: float,
    level: float,
) -> Tuple[float, float]:
    """Compute confidence interval for the mean estimate using t-distribution."""
    n = len(arr)
    se = spread / np.sqrt(n)
    alpha = 1 - level
    t_val = float(t_dist.ppf(1 - alpha / 2, df=max(1, n - 1)))
    margin = t_val * se
    return (center - margin, center + margin)
