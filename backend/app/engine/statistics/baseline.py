"""
Robust baseline estimation for personal health metrics.

Phase 2.1: Replace simple mean/std with outlier-resistant methods.

Key methods:
- median_mad: Median + Median Absolute Deviation (most robust)
- trimmed_mean: Trimmed mean with winsorized std (moderate robustness)
- huber: Huber M-estimator (adaptive robustness)

Design notes:
- Pure Python with minimal dependencies (statistics module only)
- All methods return BaselineEstimate with confidence intervals
- Method choice logged for auditability
"""

from dataclasses import dataclass
from enum import Enum
from statistics import median, mean, stdev
from typing import List, Tuple, Optional
import math


class BaselineMethod(str, Enum):
    """Available robust estimation methods."""

    MEDIAN_MAD = "median_mad"
    TRIMMED_MEAN = "trimmed_mean"
    HUBER = "huber"
    SIMPLE_MEAN = "simple_mean"  # Legacy, for comparison only


@dataclass(frozen=True)
class BaselineEstimate:
    """
    Robust baseline estimate with uncertainty quantification.

    center: Central tendency estimate (median or robust mean)
    spread: Dispersion estimate (MAD or robust std)
    method: Which estimation method was used
    n_samples: Number of data points used
    confidence_interval_80: 80% CI bounds for the center
    confidence_interval_95: 95% CI bounds for the center
    is_stable: True if we have enough data for reliable estimate (≥14 days)
    outliers_detected: Count of values flagged as potential outliers
    """

    center: float
    spread: float
    method: BaselineMethod
    n_samples: int
    confidence_interval_80: Tuple[float, float]
    confidence_interval_95: Tuple[float, float]
    is_stable: bool
    outliers_detected: int = 0


def median_absolute_deviation(values: List[float], scale: float = 1.4826) -> float:
    """
    Compute Median Absolute Deviation (MAD).

    MAD = median(|x_i - median(x)|)

    The scale factor 1.4826 makes MAD consistent with std for normal distributions.

    Args:
        values: List of numeric values
        scale: Scaling factor (1.4826 for normal consistency)

    Returns:
        Scaled MAD value
    """
    if len(values) < 2:
        return 0.0

    med = median(values)
    deviations = [abs(v - med) for v in values]
    mad = median(deviations)

    return mad * scale


def _compute_ci_bootstrap(
    values: List[float],
    center: float,
    spread: float,
    confidence: float,
) -> Tuple[float, float]:
    """
    Compute confidence interval using normal approximation.

    For small samples, this is approximate. Full bootstrap would be
    more accurate but computationally expensive for daily use.
    """
    n = len(values)
    if n < 2:
        return (center, center)

    # Standard error of the median (asymptotic)
    # SE(median) ≈ 1.2533 * σ / sqrt(n) for normal distributions
    se = 1.2533 * spread / math.sqrt(n)

    # Z-scores for confidence levels
    z_scores = {
        0.80: 1.282,
        0.95: 1.960,
        0.99: 2.576,
    }
    z = z_scores.get(confidence, 1.960)

    margin = z * se
    return (center - margin, center + margin)


def _trimmed_mean(values: List[float], trim_fraction: float = 0.1) -> float:
    """Compute trimmed mean, removing trim_fraction from each tail."""
    if len(values) < 3:
        return mean(values) if values else 0.0

    sorted_values = sorted(values)
    n = len(sorted_values)
    trim_count = max(1, int(n * trim_fraction))

    trimmed = sorted_values[trim_count:-trim_count] if trim_count < n // 2 else sorted_values
    return mean(trimmed) if trimmed else mean(values)


def _winsorized_std(values: List[float], trim_fraction: float = 0.1) -> float:
    """Compute std after winsorizing (capping) extreme values."""
    if len(values) < 3:
        return stdev(values) if len(values) > 1 else 0.0

    sorted_values = sorted(values)
    n = len(sorted_values)
    trim_count = max(1, int(n * trim_fraction))

    lower_bound = sorted_values[trim_count]
    upper_bound = sorted_values[-(trim_count + 1)]

    winsorized = [
        max(lower_bound, min(upper_bound, v))
        for v in values
    ]

    return stdev(winsorized) if len(winsorized) > 1 else 0.0


def _huber_estimate(
    values: List[float],
    k: float = 1.5,
    max_iter: int = 50,
    tol: float = 1e-6,
) -> Tuple[float, float]:
    """
    Huber M-estimator for location and scale.

    Iteratively reweighted least squares with Huber loss.
    k controls the threshold for outlier downweighting.
    """
    if len(values) < 3:
        return (mean(values) if values else 0.0, stdev(values) if len(values) > 1 else 0.0)

    # Initialize with median and MAD
    mu = median(values)
    sigma = median_absolute_deviation(values)

    if sigma == 0:
        sigma = stdev(values) if len(values) > 1 else 1.0
    if sigma == 0:
        sigma = 1.0

    for _ in range(max_iter):
        # Compute weights based on Huber function
        weights = []
        for v in values:
            z = abs(v - mu) / sigma
            if z <= k:
                weights.append(1.0)
            else:
                weights.append(k / z)

        # Weighted mean
        new_mu = sum(w * v for w, v in zip(weights, values)) / sum(weights)

        # Check convergence
        if abs(new_mu - mu) < tol:
            break
        mu = new_mu

    # Robust scale estimate
    residuals = [(v - mu) ** 2 for v in values]
    sigma = math.sqrt(sum(residuals) / len(residuals))

    return (mu, sigma)


def _count_outliers(values: List[float], center: float, spread: float, threshold: float = 3.0) -> int:
    """Count values more than threshold MADs from center."""
    if spread == 0:
        return 0

    return sum(1 for v in values if abs(v - center) / spread > threshold)


class RobustBaseline:
    """
    Robust baseline estimator with configurable methods.

    Usage:
        estimator = RobustBaseline(method="median_mad")
        estimate = estimator.fit(data)

        print(f"Center: {estimate.center:.2f} ± {estimate.spread:.2f}")
        print(f"95% CI: {estimate.confidence_interval_95}")
    """

    def __init__(
        self,
        method: str = "median_mad",
        min_stable_samples: int = 14,
    ):
        """
        Initialize robust baseline estimator.

        Args:
            method: One of "median_mad", "trimmed_mean", "huber", "simple_mean"
            min_stable_samples: Minimum samples to consider baseline "stable"
        """
        self.method = BaselineMethod(method)
        self.min_stable_samples = min_stable_samples

    def fit(self, values: List[float]) -> BaselineEstimate:
        """
        Compute robust baseline estimate from data.

        Args:
            values: List of metric values

        Returns:
            BaselineEstimate with center, spread, and confidence intervals
        """
        if not values:
            return BaselineEstimate(
                center=0.0,
                spread=0.0,
                method=self.method,
                n_samples=0,
                confidence_interval_80=(0.0, 0.0),
                confidence_interval_95=(0.0, 0.0),
                is_stable=False,
                outliers_detected=0,
            )

        if len(values) == 1:
            return BaselineEstimate(
                center=values[0],
                spread=0.0,
                method=self.method,
                n_samples=1,
                confidence_interval_80=(values[0], values[0]),
                confidence_interval_95=(values[0], values[0]),
                is_stable=False,
                outliers_detected=0,
            )

        # Compute center and spread based on method
        if self.method == BaselineMethod.MEDIAN_MAD:
            center = median(values)
            spread = median_absolute_deviation(values)
        elif self.method == BaselineMethod.TRIMMED_MEAN:
            center = _trimmed_mean(values)
            spread = _winsorized_std(values)
        elif self.method == BaselineMethod.HUBER:
            center, spread = _huber_estimate(values)
        else:  # SIMPLE_MEAN
            center = mean(values)
            spread = stdev(values)

        # Ensure non-zero spread for CI computation
        if spread == 0:
            spread = stdev(values) if len(values) > 1 else 0.0

        # Compute confidence intervals
        ci_80 = _compute_ci_bootstrap(values, center, spread, 0.80)
        ci_95 = _compute_ci_bootstrap(values, center, spread, 0.95)

        # Count outliers
        outliers = _count_outliers(values, center, spread)

        return BaselineEstimate(
            center=center,
            spread=spread,
            method=self.method,
            n_samples=len(values),
            confidence_interval_80=ci_80,
            confidence_interval_95=ci_95,
            is_stable=len(values) >= self.min_stable_samples,
            outliers_detected=outliers,
        )


def compute_robust_baseline(
    values: List[float],
    method: str = "median_mad",
    min_stable_samples: int = 14,
) -> BaselineEstimate:
    """
    Convenience function for one-off baseline computation.

    Args:
        values: List of metric values
        method: Estimation method ("median_mad", "trimmed_mean", "huber")
        min_stable_samples: Minimum samples for stable baseline

    Returns:
        BaselineEstimate with robust center and spread estimates
    """
    estimator = RobustBaseline(method=method, min_stable_samples=min_stable_samples)
    return estimator.fit(values)
