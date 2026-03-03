"""
Bayesian confidence framework for insight generation.

Phase 2.2: Replaces ad-hoc confidence scores with principled Bayesian
posterior probabilities and credible intervals.

The key idea: given observed data, what is the probability that a
real change/trend exists (vs. normal variation)?

Uses conjugate normal-normal model for computational efficiency:
- Prior: the baseline distribution represents our prior belief
- Likelihood: the recent data is the new evidence
- Posterior: updated belief about the true state
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from scipy.stats import norm


@dataclass(frozen=True)
class ConfidenceResult:
    """Result of Bayesian confidence computation."""
    probability_real: float  # P(effect is real), 0-1
    credible_interval_80: Tuple[float, float]
    credible_interval_95: Tuple[float, float]
    bayes_factor: float  # Evidence ratio (>3 = substantial, >10 = strong)
    effect_size: float  # Cohen's d equivalent
    interpretation: str  # Human-readable summary


def compute_bayesian_confidence(
    observed_mean: float,
    baseline_center: float,
    baseline_spread: float,
    n_observations: int,
    observation_std: Optional[float] = None,
) -> ConfidenceResult:
    """
    Compute Bayesian posterior probability that an effect is real.

    Uses a normal-normal conjugate model:
    - Prior: N(baseline_center, baseline_spread^2)
    - Likelihood: observations ~ N(true_mean, sigma^2/n)
    - Posterior: N(posterior_mean, posterior_var)

    The "effect is real" question becomes: what is P(|true_mean - baseline| > 0)?

    Args:
        observed_mean: Mean of recent observations
        baseline_center: Baseline center (median or mean)
        baseline_spread: Baseline spread (MAD or std)
        n_observations: Number of recent observations
        observation_std: Std of recent observations (defaults to baseline_spread)
    """
    if baseline_spread < 1e-10:
        baseline_spread = 1e-10

    if observation_std is None or observation_std < 1e-10:
        observation_std = baseline_spread

    # Standard error of the observed mean
    se = observation_std / np.sqrt(max(1, n_observations))

    # Prior precision and likelihood precision
    prior_precision = 1.0 / (baseline_spread ** 2)
    likelihood_precision = 1.0 / (se ** 2)

    # Posterior (conjugate update)
    posterior_precision = prior_precision + likelihood_precision
    posterior_var = 1.0 / posterior_precision
    posterior_mean = (
        prior_precision * baseline_center + likelihood_precision * observed_mean
    ) / posterior_precision
    posterior_std = np.sqrt(posterior_var)

    # P(effect is real) = P(|posterior_mean - baseline| > 0)
    # More precisely: P(true_mean > baseline) or P(true_mean < baseline)
    # depending on direction
    delta = observed_mean - baseline_center
    if abs(delta) < 1e-10:
        prob_real = 0.5
    else:
        # P(true_mean is on the same side as observed_mean relative to baseline)
        if delta > 0:
            prob_real = 1.0 - norm.cdf(baseline_center, loc=posterior_mean, scale=posterior_std)
        else:
            prob_real = norm.cdf(baseline_center, loc=posterior_mean, scale=posterior_std)

    prob_real = float(np.clip(prob_real, 0.0, 1.0))

    # Credible intervals on the posterior
    ci_80 = (
        float(norm.ppf(0.10, loc=posterior_mean, scale=posterior_std)),
        float(norm.ppf(0.90, loc=posterior_mean, scale=posterior_std)),
    )
    ci_95 = (
        float(norm.ppf(0.025, loc=posterior_mean, scale=posterior_std)),
        float(norm.ppf(0.975, loc=posterior_mean, scale=posterior_std)),
    )

    # Bayes factor: evidence for H1 (effect exists) vs H0 (no effect)
    # Using Savage-Dickey density ratio at the null point
    prior_density_at_null = norm.pdf(baseline_center, loc=baseline_center, scale=baseline_spread)
    posterior_density_at_null = norm.pdf(baseline_center, loc=posterior_mean, scale=posterior_std)

    if posterior_density_at_null > 1e-300:
        bayes_factor = float(prior_density_at_null / posterior_density_at_null)
    else:
        bayes_factor = 100.0  # Very strong evidence

    bayes_factor = min(bayes_factor, 100.0)

    # Effect size (Cohen's d equivalent)
    effect_size = float(abs(delta) / baseline_spread) if baseline_spread > 1e-10 else 0.0

    interpretation = _interpret(prob_real, bayes_factor, effect_size)

    return ConfidenceResult(
        probability_real=round(prob_real, 4),
        credible_interval_80=ci_80,
        credible_interval_95=ci_95,
        bayes_factor=round(bayes_factor, 2),
        effect_size=round(effect_size, 3),
        interpretation=interpretation,
    )


def _interpret(prob: float, bf: float, effect_size: float) -> str:
    """Generate human-readable interpretation."""
    if prob < 0.6:
        confidence_str = "very low confidence"
    elif prob < 0.75:
        confidence_str = "low confidence"
    elif prob < 0.9:
        confidence_str = "moderate confidence"
    elif prob < 0.95:
        confidence_str = "high confidence"
    else:
        confidence_str = "very high confidence"

    if effect_size < 0.2:
        size_str = "negligible"
    elif effect_size < 0.5:
        size_str = "small"
    elif effect_size < 0.8:
        size_str = "medium"
    else:
        size_str = "large"

    return f"{confidence_str} ({size_str} effect)"
