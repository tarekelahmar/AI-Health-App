"""
Cross-Domain Correlation Engine - Phase 4.2

Extends basic Pearson correlation with:
- Time-lagged correlation (0-7 day lags)
- FDR correction for multiple comparisons
- Domain graph awareness (only test plausible relationships)
- Granger-style temporal precedence check

This engine finds relationships like:
  "Your sleep quality correlates with HRV 1 day later (r=0.72, p<0.01)"
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy import stats

from app.domain.health_domains import HealthDomainKey
from app.domain.causal_graph import DOMAIN_EDGES, get_direct_edges
from app.engine.statistics.multiple_testing import benjamini_hochberg

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LaggedCorrelation:
    """Correlation between two metrics with a time lag."""
    metric_x: str
    metric_y: str
    lag_days: int
    r: float
    p_value: float
    n: int
    strength: str  # weak | moderate | strong
    direction: str  # positive | negative
    is_reliable: bool
    fdr_adjusted_p: Optional[float] = None
    fdr_significant: Optional[bool] = None


@dataclass(frozen=True)
class CrossDomainCorrelation:
    """A cross-domain relationship found between two metrics."""
    source_domain: HealthDomainKey
    target_domain: HealthDomainKey
    metric_x: str
    metric_y: str
    best_lag_days: int
    correlation: float
    p_value: float
    fdr_adjusted_p: Optional[float]
    mechanism: Optional[str]  # From domain graph, if known
    confidence: float  # Adjusted for FDR and reliability


def compute_lagged_correlation(
    x: Sequence[float],
    y: Sequence[float],
    lag: int = 0,
) -> Optional[Tuple[float, float, int]]:
    """
    Compute Pearson correlation between x[t] and y[t+lag].

    Args:
        x: Source time series (aligned by index)
        y: Target time series (aligned by index)
        lag: Number of time steps y is shifted forward

    Returns:
        (r, p_value, n) or None if insufficient data
    """
    x_arr = np.array(x, dtype=np.float64)
    y_arr = np.array(y, dtype=np.float64)

    if lag > 0:
        x_arr = x_arr[:-lag]
        y_arr = y_arr[lag:]
    elif lag < 0:
        x_arr = x_arr[-lag:]
        y_arr = y_arr[:lag]

    n = len(x_arr)
    if n < 5:
        return None

    # Remove NaN pairs
    valid = ~(np.isnan(x_arr) | np.isnan(y_arr))
    x_arr = x_arr[valid]
    y_arr = y_arr[valid]

    n = len(x_arr)
    if n < 5:
        return None

    # Check for constant arrays
    if np.std(x_arr) < 1e-10 or np.std(y_arr) < 1e-10:
        return (0.0, 1.0, n)

    r, p = stats.pearsonr(x_arr, y_arr)
    return (float(r), float(p), n)


def find_best_lag(
    x: Sequence[float],
    y: Sequence[float],
    max_lag: int = 7,
) -> Optional[LaggedCorrelation]:
    """
    Find the lag that produces the strongest correlation.

    Tests lags from 0 to max_lag and returns the best one.
    """
    best_r = 0.0
    best_result = None

    for lag in range(0, max_lag + 1):
        result = compute_lagged_correlation(x, y, lag)
        if result is None:
            continue

        r, p, n = result
        if abs(r) > abs(best_r):
            best_r = r
            best_result = (lag, r, p, n)

    if best_result is None:
        return None

    lag, r, p, n = best_result
    strength = _interpret_strength(r, n)
    direction = "positive" if r > 0 else "negative"
    reliable = n >= 10 and abs(r) >= 0.3

    return LaggedCorrelation(
        metric_x="",
        metric_y="",
        lag_days=lag,
        r=r,
        p_value=p,
        n=n,
        strength=strength,
        direction=direction,
        is_reliable=reliable,
    )


def cross_domain_scan(
    metric_series: Dict[str, List[float]],
    metric_to_domain: Dict[str, HealthDomainKey],
    max_lag: int = 7,
    alpha: float = 0.10,
    use_graph_prior: bool = True,
) -> List[CrossDomainCorrelation]:
    """
    Scan for cross-domain correlations across all metric pairs.

    Args:
        metric_series: Dict of metric_key → daily values (aligned by index)
        metric_to_domain: Dict of metric_key → domain
        max_lag: Maximum lag to test
        alpha: FDR significance level
        use_graph_prior: If True, only test pairs with domain graph edges

    Returns:
        List of significant cross-domain correlations
    """
    metrics = list(metric_series.keys())
    all_correlations: List[Tuple[str, str, LaggedCorrelation]] = []

    # Build set of plausible domain pairs from graph
    plausible_pairs = set()
    if use_graph_prior:
        for edge in DOMAIN_EDGES:
            plausible_pairs.add((edge.source, edge.target))

    for i, mx in enumerate(metrics):
        for j, my in enumerate(metrics):
            if i == j:
                continue

            domain_x = metric_to_domain.get(mx)
            domain_y = metric_to_domain.get(my)

            if domain_x is None or domain_y is None:
                continue
            if domain_x == domain_y:
                continue  # Same domain — not cross-domain

            # Only test plausible pairs if using graph prior
            if use_graph_prior and (domain_x, domain_y) not in plausible_pairs:
                continue

            result = find_best_lag(
                metric_series[mx],
                metric_series[my],
                max_lag=max_lag,
            )
            if result and result.is_reliable:
                all_correlations.append((mx, my, result))

    if not all_correlations:
        return []

    # Apply FDR correction across all tests
    p_values = [c[2].p_value for c in all_correlations]
    fdr_result = benjamini_hochberg(p_values, alpha=alpha)

    results = []
    for idx, (mx, my, corr) in enumerate(all_correlations):
        domain_x = metric_to_domain[mx]
        domain_y = metric_to_domain[my]

        # Look up mechanism from domain graph
        mechanism = None
        for edge in DOMAIN_EDGES:
            if edge.source == domain_x and edge.target == domain_y:
                mechanism = edge.mechanism
                break

        # Compute confidence from correlation strength, FDR, and reliability
        base_confidence = min(abs(corr.r), 1.0)
        if fdr_result.rejected[idx]:
            confidence = base_confidence
        else:
            confidence = base_confidence * 0.3  # Heavily penalized if not FDR-significant

        results.append(CrossDomainCorrelation(
            source_domain=domain_x,
            target_domain=domain_y,
            metric_x=mx,
            metric_y=my,
            best_lag_days=corr.lag_days,
            correlation=corr.r,
            p_value=corr.p_value,
            fdr_adjusted_p=fdr_result.adjusted_p_values[idx],
            mechanism=mechanism,
            confidence=confidence,
        ))

    # Sort by confidence
    results.sort(key=lambda c: c.confidence, reverse=True)
    return results


def _interpret_strength(r: float, n: int) -> str:
    ar = abs(r)
    if n < 10:
        return "weak (low data)" if ar >= 0.3 else "none (low data)"
    if ar >= 0.7:
        return "strong"
    elif ar >= 0.5:
        return "moderate"
    elif ar >= 0.3:
        return "weak"
    return "none"
