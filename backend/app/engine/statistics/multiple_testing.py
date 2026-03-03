"""
Multiple testing correction using False Discovery Rate (FDR) control.

Phase 2.4: When testing many metrics simultaneously, some will appear
significant by chance. FDR control limits the expected proportion of
false discoveries among all declared discoveries.

Example: If we test 10 metrics and find 3 "significant" changes,
FDR at 10% means we expect at most 0.3 of those 3 to be false positives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np


@dataclass(frozen=True)
class FDRAdjustedResult:
    """Result of FDR adjustment on multiple p-values."""
    original_p_values: List[float]
    adjusted_p_values: List[float]
    rejected: List[bool]  # True if significant after correction
    n_discoveries: int
    expected_false_discoveries: float
    method: str


def benjamini_hochberg(
    p_values: List[float],
    alpha: float = 0.10,
) -> FDRAdjustedResult:
    """
    Apply Benjamini-Hochberg FDR correction to a list of p-values.

    This is the standard procedure for controlling the False Discovery Rate:
    1. Sort p-values in ascending order
    2. For each rank k, compute threshold: (k / m) * alpha
    3. Find largest k where p(k) <= threshold
    4. Reject all hypotheses with rank <= k

    Args:
        p_values: List of raw p-values from multiple tests
        alpha: Target FDR (default 0.10 = 10%)

    Returns:
        FDRAdjustedResult with adjusted p-values and rejection decisions
    """
    if not p_values:
        return FDRAdjustedResult(
            original_p_values=[],
            adjusted_p_values=[],
            rejected=[],
            n_discoveries=0,
            expected_false_discoveries=0.0,
            method="benjamini_hochberg",
        )

    m = len(p_values)
    arr = np.array(p_values, dtype=np.float64)

    # Sort indices by p-value
    sorted_indices = np.argsort(arr)
    sorted_p = arr[sorted_indices]

    # Compute adjusted p-values (step-up procedure)
    adjusted = np.zeros(m)
    adjusted[m - 1] = sorted_p[m - 1]
    for i in range(m - 2, -1, -1):
        rank = i + 1
        adjusted[i] = min(
            adjusted[i + 1],
            sorted_p[i] * m / rank,
        )
    adjusted = np.clip(adjusted, 0.0, 1.0)

    # Map back to original order
    adjusted_original = np.zeros(m)
    for i, idx in enumerate(sorted_indices):
        adjusted_original[idx] = adjusted[i]

    rejected = [bool(p <= alpha) for p in adjusted_original]
    n_discoveries = sum(rejected)
    expected_false = n_discoveries * alpha if n_discoveries > 0 else 0.0

    return FDRAdjustedResult(
        original_p_values=list(arr),
        adjusted_p_values=list(adjusted_original),
        rejected=rejected,
        n_discoveries=n_discoveries,
        expected_false_discoveries=round(expected_false, 3),
        method="benjamini_hochberg",
    )


def z_score_to_p_value(z_score: float) -> float:
    """Convert a z-score to a two-tailed p-value."""
    from scipy.stats import norm
    return float(2.0 * (1.0 - norm.cdf(abs(z_score))))


def apply_fdr_to_insights(
    insights: List[dict],
    alpha: float = 0.10,
) -> Tuple[List[dict], FDRAdjustedResult]:
    """
    Apply FDR correction to a batch of insights.

    Extracts z-scores from insight evidence, converts to p-values,
    applies BH correction, and marks insights as FDR-adjusted.

    Args:
        insights: List of insight dicts with 'evidence' containing 'z_score'
        alpha: Target FDR

    Returns:
        Tuple of (adjusted insights list, FDR result)
    """
    # Extract z-scores and compute p-values
    p_values = []
    has_z_score = []

    for ins in insights:
        evidence = ins.get("evidence", {})
        z = evidence.get("z_score")
        if z is not None and z != 0:
            p_values.append(z_score_to_p_value(z))
            has_z_score.append(True)
        else:
            p_values.append(1.0)  # Non-significant default
            has_z_score.append(False)

    if not any(has_z_score):
        fdr_result = FDRAdjustedResult(
            original_p_values=p_values,
            adjusted_p_values=p_values,
            rejected=[False] * len(p_values),
            n_discoveries=0,
            expected_false_discoveries=0.0,
            method="benjamini_hochberg",
        )
        return insights, fdr_result

    fdr_result = benjamini_hochberg(p_values, alpha=alpha)

    # Annotate insights with FDR results
    adjusted_insights = []
    for i, ins in enumerate(insights):
        ins_copy = dict(ins)
        ins_copy["fdr_adjusted_p"] = fdr_result.adjusted_p_values[i]
        ins_copy["fdr_significant"] = fdr_result.rejected[i]
        adjusted_insights.append(ins_copy)

    return adjusted_insights, fdr_result
