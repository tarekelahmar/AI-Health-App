"""
Experiment design engine for rigorous self-experimentation.

Phase 6.1: Designs n-of-1 experiments with power analysis,
pre-registered success criteria, and adherence requirements.

Design principles:
  - Pre-register everything (outcomes, thresholds, duration)
  - Power analysis determines minimum duration
  - Conservative defaults (longer baselines, higher adherence)
  - Clear success/failure criteria before starting

Lifecycle: Design → Baseline → Intervention → [Washout] → Analysis → Verdict
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import norm

logger = logging.getLogger(__name__)


# ── Data Classes ────────────────────────────────────────────────────


class ExperimentPhase(str, Enum):
    DESIGN = "design"
    BASELINE = "baseline"
    INTERVENTION = "intervention"
    WASHOUT = "washout"
    ANALYSIS = "analysis"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class PowerAnalysisResult:
    """Result of power analysis for experiment duration."""
    required_days: int
    power: float  # Statistical power (typically 0.8)
    alpha: float  # Significance level (typically 0.05)
    min_detectable_effect: float  # Cohen's d
    baseline_variance: float
    method: str


@dataclass(frozen=True)
class SuccessCriteria:
    """Pre-registered success criteria for an experiment."""
    primary_metric: str
    direction: str  # "increase" or "decrease"
    min_effect_size: float  # Cohen's d threshold
    required_confidence: float  # p-value threshold (e.g., 0.05)
    min_adherence: float  # Minimum adherence rate (e.g., 0.8)
    secondary_metrics: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExperimentDesign:
    """Complete experiment design, ready for execution."""
    hypothesis: str
    intervention: str
    intervention_key: str

    # Timeline
    baseline_days: int
    intervention_days: int
    washout_days: int
    total_days: int

    # Metrics
    target_metrics: List[str]
    success_criteria: SuccessCriteria
    power_analysis: PowerAnalysisResult

    # Requirements
    tracking_requirements: List[str]
    confounders_to_monitor: List[str]

    # Metadata
    designed_date: date
    estimated_completion: date


# ── Constants ───────────────────────────────────────────────────────

DEFAULT_BASELINE_DAYS = 14
MIN_BASELINE_DAYS = 7
DEFAULT_WASHOUT_DAYS = 7
MIN_INTERVENTION_DAYS = 7
MAX_INTERVENTION_DAYS = 90
DEFAULT_POWER = 0.80
DEFAULT_ALPHA = 0.05
DEFAULT_EFFECT_SIZE = 0.5  # Medium Cohen's d
MIN_ADHERENCE = 0.80

# Common confounders to always monitor
DEFAULT_CONFOUNDERS = [
    "sleep_quality",
    "stress_level",
    "travel",
    "illness",
    "medication_changes",
]

# Known intervention → metric mappings for default suggestions
INTERVENTION_METRICS = {
    "magnesium_glycinate": {
        "primary": "sleep_duration_minutes",
        "secondary": ["sleep_efficiency_pct", "hrv_rmssd_ms"],
        "direction": "increase",
        "typical_effect": 0.4,
    },
    "melatonin": {
        "primary": "sleep_onset_latency_min",
        "secondary": ["sleep_duration_minutes"],
        "direction": "decrease",
        "typical_effect": 0.5,
    },
    "creatine_monohydrate": {
        "primary": "subjective_energy",
        "secondary": ["cognitive_performance"],
        "direction": "increase",
        "typical_effect": 0.3,
    },
    "ashwagandha": {
        "primary": "subjective_stress",
        "secondary": ["sleep_efficiency_pct", "hrv_rmssd_ms"],
        "direction": "decrease",
        "typical_effect": 0.5,
    },
    "cold_exposure": {
        "primary": "hrv_rmssd_ms",
        "secondary": ["subjective_energy", "resting_heart_rate_bpm"],
        "direction": "increase",
        "typical_effect": 0.3,
    },
}


# ── Power Analysis ──────────────────────────────────────────────────


def power_analysis(
    baseline_std: float,
    effect_size: float = DEFAULT_EFFECT_SIZE,
    alpha: float = DEFAULT_ALPHA,
    power: float = DEFAULT_POWER,
) -> PowerAnalysisResult:
    """
    Compute required intervention days for a paired t-test (n-of-1).

    For an n-of-1 experiment, each "day" is a sample. We need enough
    days to detect the effect given the day-to-day variability.

    Formula: n = ((z_alpha + z_beta) / d)^2
    where d = effect_size (Cohen's d = delta / std)

    Args:
        baseline_std: Day-to-day standard deviation of the metric
        effect_size: Minimum detectable effect in Cohen's d units
        alpha: Type I error rate (two-tailed)
        power: Statistical power (1 - Type II error rate)

    Returns:
        PowerAnalysisResult with required_days
    """
    if effect_size <= 0:
        raise ValueError("effect_size must be positive")
    if baseline_std < 0:
        raise ValueError("baseline_std must be non-negative")

    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = norm.ppf(power)

    # Required sample size per group (baseline and intervention)
    n_per_group = math.ceil(((z_alpha + z_beta) / effect_size) ** 2)

    # Enforce minimum
    required_days = max(MIN_INTERVENTION_DAYS, n_per_group)
    # Enforce maximum
    required_days = min(MAX_INTERVENTION_DAYS, required_days)

    return PowerAnalysisResult(
        required_days=required_days,
        power=power,
        alpha=alpha,
        min_detectable_effect=effect_size,
        baseline_variance=baseline_std ** 2,
        method="paired_t_test_nof1",
    )


# ── Experiment Designer ────────────────────────────────────────────


class ExperimentDesigner:
    """
    Designs rigorous n-of-1 experiments with pre-registered criteria.

    Handles power analysis, duration calculation, metric selection,
    and success criteria definition.
    """

    def design(
        self,
        hypothesis: str,
        intervention: str,
        intervention_key: str,
        target_metrics: List[str],
        baseline_std: Optional[float] = None,
        effect_size: float = DEFAULT_EFFECT_SIZE,
        baseline_days: int = DEFAULT_BASELINE_DAYS,
        washout_days: int = DEFAULT_WASHOUT_DAYS,
        direction: str = "increase",
        start_date: Optional[date] = None,
    ) -> ExperimentDesign:
        """
        Design a complete experiment.

        Args:
            hypothesis: What we're testing (e.g., "Magnesium improves sleep duration")
            intervention: Description of the intervention
            intervention_key: Machine-readable intervention identifier
            target_metrics: List of metrics to track
            baseline_std: Day-to-day std of primary metric (auto-estimated if None)
            effect_size: Minimum detectable effect in Cohen's d
            baseline_days: Number of baseline days
            washout_days: Number of washout days (0 to skip)
            direction: Expected effect direction ("increase" or "decrease")
            start_date: When to start (defaults to today)

        Returns:
            Complete ExperimentDesign ready for execution
        """
        if not target_metrics:
            raise ValueError("At least one target metric required")

        if direction not in ("increase", "decrease"):
            raise ValueError("direction must be 'increase' or 'decrease'")

        start_date = start_date or date.today()

        # Use known intervention info if available
        known = INTERVENTION_METRICS.get(intervention_key, {})
        if baseline_std is None:
            baseline_std = 1.0  # Default assumption: unit std

        # Power analysis
        pa = power_analysis(
            baseline_std=baseline_std,
            effect_size=effect_size,
        )

        intervention_days = pa.required_days
        baseline_days = max(baseline_days, MIN_BASELINE_DAYS)
        total_days = baseline_days + intervention_days + washout_days

        # Success criteria
        criteria = SuccessCriteria(
            primary_metric=target_metrics[0],
            direction=direction,
            min_effect_size=effect_size,
            required_confidence=DEFAULT_ALPHA,
            min_adherence=MIN_ADHERENCE,
            secondary_metrics=target_metrics[1:] if len(target_metrics) > 1 else [],
        )

        # Tracking requirements
        tracking = ["daily_checkin", "intervention_log"]
        if known:
            tracking.append(f"track_{criteria.primary_metric}")

        estimated_completion = start_date + timedelta(days=total_days)

        return ExperimentDesign(
            hypothesis=hypothesis,
            intervention=intervention,
            intervention_key=intervention_key,
            baseline_days=baseline_days,
            intervention_days=intervention_days,
            washout_days=washout_days,
            total_days=total_days,
            target_metrics=target_metrics,
            success_criteria=criteria,
            power_analysis=pa,
            tracking_requirements=tracking,
            confounders_to_monitor=list(DEFAULT_CONFOUNDERS),
            designed_date=start_date,
            estimated_completion=estimated_completion,
        )

    def suggest_design(
        self,
        intervention_key: str,
        baseline_std: Optional[float] = None,
    ) -> Optional[ExperimentDesign]:
        """
        Auto-suggest an experiment design for a known intervention.

        Returns None if intervention is not in our registry.
        """
        known = INTERVENTION_METRICS.get(intervention_key)
        if not known:
            return None

        metrics = [known["primary"]] + known.get("secondary", [])

        return self.design(
            hypothesis=f"{intervention_key} {known['direction']}s {known['primary']}",
            intervention=intervention_key.replace("_", " ").title(),
            intervention_key=intervention_key,
            target_metrics=metrics,
            baseline_std=baseline_std,
            effect_size=known.get("typical_effect", DEFAULT_EFFECT_SIZE),
            direction=known["direction"],
        )
