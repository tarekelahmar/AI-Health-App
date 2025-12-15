"""
Attribution guardrails to prevent false positives.

SECURITY FIX (Risk #8): Adds FDR control, stability checks, and minimum requirements
to prevent spurious correlations from being presented as confident drivers.
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AttributionGuardrailResult:
    """Result of guardrail checks."""
    passed: bool
    reason: Optional[str] = None
    adjusted_confidence: Optional[float] = None
    label: Optional[str] = None  # "confounded", "unstable", "preliminary", etc.


def benjamini_hochberg_fdr(
    p_values: List[float],
    alpha: float = 0.05,
) -> List[bool]:
    """
    Benjamini-Hochberg FDR correction for multiple comparisons.
    
    Args:
        p_values: List of p-values (must be sorted ascending)
        alpha: False discovery rate threshold (default 0.05)
    
    Returns:
        List of booleans indicating which hypotheses pass FDR correction
    """
    if not p_values:
        return []
    
    m = len(p_values)
    results = [False] * m
    
    # Sort p-values with indices
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    
    # Find largest k such that p(k) <= (k/m) * alpha
    for k in range(m - 1, -1, -1):
        idx, p_val = indexed[k]
        threshold = ((k + 1) / m) * alpha
        if p_val <= threshold:
            # All hypotheses up to k pass
            for i in range(k + 1):
                results[indexed[i][0]] = True
            break
    
    return results


def compute_p_value_from_r_squared(
    r_squared: float,
    n: int,
) -> float:
    """
    Approximate p-value from R² using F-test.
    
    For simple regression: F = (R² / 1) / ((1 - R²) / (n - 2))
    p-value from F-distribution.
    
    This is an approximation; for exact p-values, use scipy.stats.
    """
    if n < 3 or r_squared <= 0 or r_squared >= 1:
        return 1.0
    
    # F-statistic
    f_stat = (r_squared / 1.0) / ((1.0 - r_squared) / (n - 2))
    
    # Approximate p-value using F-distribution
    # For large n, F(1, n-2) approximates chi-square(1) / (n-2)
    # Simple approximation: p ≈ 2 * (1 - norm.cdf(sqrt(f_stat)))
    # For MVP, use conservative approximation
    if f_stat < 1.0:
        return 0.5  # Conservative
    elif f_stat < 4.0:
        return 0.1  # Moderate
    elif f_stat < 10.0:
        return 0.01  # Significant
    else:
        return 0.001  # Highly significant


def apply_attribution_guardrails(
    effect_size: float,
    confidence: float,
    stability: float,
    variance_explained: float,
    sample_size: int,
    n_comparisons: int = 1,
    p_value: Optional[float] = None,
    r_squared: Optional[float] = None,
    min_sample_size: int = 14,
    min_stability: float = 0.5,
    min_variance_explained: float = 0.1,
    fdr_alpha: float = 0.05,
) -> AttributionGuardrailResult:
    """
    Apply guardrails to attribution results.
    
    SECURITY FIX (Risk #8): Prevents false positives through:
    - Minimum sample size requirements
    - Stability checks
    - Variance explained thresholds
    - FDR correction for multiple comparisons
    - Confidence adjustment based on guardrail violations
    
    Args:
        effect_size: Effect size (Cohen's d)
        confidence: Original confidence score
        stability: Stability score (0-1)
        variance_explained: R² value
        sample_size: Number of data points
        n_comparisons: Number of comparisons made (for FDR correction)
        p_value: P-value if available
        r_squared: R² if p_value not available
        min_sample_size: Minimum required sample size
        min_stability: Minimum stability threshold
        min_variance_explained: Minimum variance explained threshold
        fdr_alpha: FDR threshold
    
    Returns:
        AttributionGuardrailResult with pass/fail and adjusted confidence
    """
    violations: List[str] = []
    adjusted_confidence = confidence
    label = None
    
    # Check minimum sample size
    if sample_size < min_sample_size:
        violations.append(f"insufficient_sample_size_{sample_size}_<_{min_sample_size}")
        adjusted_confidence *= 0.5  # Halve confidence
        label = "preliminary"
    
    # Check stability
    if stability < min_stability:
        violations.append(f"low_stability_{stability:.2f}_<_{min_stability}")
        adjusted_confidence *= 0.7  # Reduce confidence
        if label is None:
            label = "unstable"
    
    # Check variance explained
    if variance_explained < min_variance_explained:
        violations.append(f"low_variance_explained_{variance_explained:.2f}_<_{min_variance_explained}")
        adjusted_confidence *= 0.8  # Slight reduction
        if label is None:
            label = "weak_association"
    
    # FDR correction for multiple comparisons
    if n_comparisons > 1:
        # Compute p-value if not provided
        if p_value is None and r_squared is not None:
            p_value = compute_p_value_from_r_squared(r_squared, sample_size)
        
        if p_value is not None:
            # For single comparison, just check p-value
            if n_comparisons == 1:
                if p_value > fdr_alpha:
                    violations.append(f"p_value_not_significant_{p_value:.4f}_>_{fdr_alpha}")
                    adjusted_confidence *= 0.6
                    if label is None:
                        label = "not_significant"
            else:
                # Multiple comparisons: would need all p-values for FDR
                # For now, apply Bonferroni correction (conservative)
                bonferroni_alpha = fdr_alpha / n_comparisons
                if p_value > bonferroni_alpha:
                    violations.append(f"p_value_fails_bonferroni_{p_value:.4f}_>_{bonferroni_alpha}")
                    adjusted_confidence *= 0.5
                    if label is None:
                        label = "not_significant_after_correction"
    
    # Check for confounded signals (very low variance explained despite high effect size)
    if abs(effect_size) > 0.5 and variance_explained < 0.05:
        violations.append("high_effect_low_variance_explained_possibly_confounded")
        adjusted_confidence *= 0.4
        label = "confounded"
    
    # Final confidence adjustment: cap at original confidence
    adjusted_confidence = min(adjusted_confidence, confidence)
    
    # Determine if passed
    passed = len(violations) == 0 and adjusted_confidence >= 0.3
    
    reason = "; ".join(violations) if violations else None
    
    return AttributionGuardrailResult(
        passed=passed,
        reason=reason,
        adjusted_confidence=adjusted_confidence,
        label=label,
    )


def filter_attributions_by_guardrails(
    attributions: List[dict],
    n_comparisons: int,
) -> List[dict]:
    """
    Filter attributions using guardrails and FDR correction.
    
    Args:
        attributions: List of attribution dicts with keys:
            - effect_size
            - confidence
            - stability
            - variance_explained (or r_squared)
            - sample_size
            - p_value (optional)
        n_comparisons: Total number of comparisons made
    
    Returns:
        Filtered list of attributions that pass guardrails
    """
    # Apply guardrails to each attribution
    guarded: List[Tuple[dict, AttributionGuardrailResult]] = []
    
    for attr in attributions:
        result = apply_attribution_guardrails(
            effect_size=attr.get("effect_size", 0.0),
            confidence=attr.get("confidence", 0.0),
            stability=attr.get("stability", 0.0),
            variance_explained=attr.get("variance_explained", attr.get("r_squared", 0.0)),
            sample_size=attr.get("sample_size", 0),
            n_comparisons=n_comparisons,
            p_value=attr.get("p_value"),
            r_squared=attr.get("r_squared", attr.get("variance_explained")),
        )
        
        # Update confidence with adjusted value
        if result.adjusted_confidence is not None:
            attr["confidence"] = result.adjusted_confidence
            attr["original_confidence"] = attr.get("confidence", result.adjusted_confidence)
        
        # Add label if present
        if result.label:
            attr["label"] = result.label
        
        # Add guardrail metadata
        attr["guardrail_passed"] = result.passed
        if result.reason:
            attr["guardrail_reason"] = result.reason
        
        guarded.append((attr, result))
    
    # Filter to only passed attributions
    passed = [attr for attr, result in guarded if result.passed]
    
    # If multiple comparisons, apply FDR correction
    if n_comparisons > 1 and len(passed) > 1:
        # Extract p-values (compute if needed)
        p_values = []
        for attr in passed:
            p_val = attr.get("p_value")
            if p_val is None:
                r_sq = attr.get("r_squared", attr.get("variance_explained", 0.0))
                p_val = compute_p_value_from_r_squared(r_sq, attr.get("sample_size", 0))
            p_values.append(p_val)
        
        # Apply FDR correction
        fdr_passed = benjamini_hochberg_fdr(sorted(p_values), alpha=0.05)
        
        # Filter based on FDR results
        passed = [attr for attr, fdr_ok in zip(passed, fdr_passed) if fdr_ok]
    
    return passed

