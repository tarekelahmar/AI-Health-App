"""
Experiment execution and tracking engine.

Phase 6.2: Manages active experiments through their lifecycle,
tracks adherence, provides progress updates, and generates verdicts.

Lifecycle:
  baseline → intervention → [washout] → analysis → completed

Features:
  - Adherence tracking with daily logs
  - Progress reporting (phase, days remaining, adherence rate)
  - Early stopping rules (clearly working/not working)
  - Automated analysis and verdict generation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import ttest_ind

from app.engine.experiments.designer import (
    ExperimentDesign,
    ExperimentPhase,
    SuccessCriteria,
)

logger = logging.getLogger(__name__)


# ── Data Classes ────────────────────────────────────────────────────


class Verdict(str, Enum):
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    UNCLEAR = "unclear"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class AdherenceLog:
    """Daily adherence record."""
    log_date: date
    adhered: bool
    notes: Optional[str] = None


@dataclass(frozen=True)
class ExperimentProgress:
    """Current progress of an active experiment."""
    current_phase: ExperimentPhase
    phase_day: int  # Day within current phase
    phase_total_days: int  # Total days in current phase
    overall_day: int  # Day within entire experiment
    overall_total_days: int
    days_remaining: int
    adherence_rate: float  # 0-1, intervention phase only
    adherence_streak: int  # Consecutive days adhered
    is_on_track: bool  # Meeting adherence requirements
    phase_progress_pct: float  # 0-100


@dataclass
class EarlyStopSignal:
    """Signal that experiment could be stopped early."""
    should_stop: bool
    reason: str
    current_effect_size: float
    current_p_value: float
    confidence: float


@dataclass(frozen=True)
class MetricResult:
    """Result for a single metric in the experiment."""
    metric: str
    baseline_mean: float
    baseline_std: float
    intervention_mean: float
    intervention_std: float
    effect_size: float  # Cohen's d
    p_value: float
    direction: str  # "increase" or "decrease"
    significant: bool
    n_baseline: int
    n_intervention: int


@dataclass(frozen=True)
class ExperimentResult:
    """Complete result of an experiment after analysis."""
    verdict: Verdict
    primary_result: MetricResult
    secondary_results: List[MetricResult]
    overall_effect_size: float
    overall_confidence: float  # 1 - p_value of primary
    adherence_rate: float
    met_adherence_requirement: bool
    met_effect_threshold: bool
    confounders_noted: List[str]
    summary: str


# ── Constants ───────────────────────────────────────────────────────

# Early stopping: if effect is this many times larger than needed, stop early
EARLY_STOP_EFFECT_MULTIPLIER = 2.0
# Early stopping: minimum days before considering early stop
EARLY_STOP_MIN_DAYS = 7
# Early stopping: p-value threshold for early positive signal
EARLY_STOP_P_THRESHOLD = 0.01
# Early stopping: p-value for futility (clearly not working)
FUTILITY_P_THRESHOLD = 0.80


# ── Experiment Tracker ──────────────────────────────────────────────


class ExperimentTracker:
    """
    Tracks experiments through their lifecycle and generates verdicts.

    Manages phase transitions, adherence, progress reporting,
    early stopping, and final analysis.
    """

    def __init__(self):
        pass

    def get_current_phase(
        self,
        design: ExperimentDesign,
        start_date: date,
        current_date: Optional[date] = None,
    ) -> Tuple[ExperimentPhase, int]:
        """
        Determine current phase and day within phase.

        Returns (phase, day_within_phase) where day is 1-indexed.
        """
        current_date = current_date or date.today()
        elapsed = (current_date - start_date).days

        if elapsed < 0:
            return ExperimentPhase.DESIGN, 0

        baseline_end = design.baseline_days
        intervention_end = baseline_end + design.intervention_days
        washout_end = intervention_end + design.washout_days

        if elapsed < baseline_end:
            return ExperimentPhase.BASELINE, elapsed + 1
        elif elapsed < intervention_end:
            return ExperimentPhase.INTERVENTION, elapsed - baseline_end + 1
        elif design.washout_days > 0 and elapsed < washout_end:
            return ExperimentPhase.WASHOUT, elapsed - intervention_end + 1
        else:
            return ExperimentPhase.ANALYSIS, 0

    def get_progress(
        self,
        design: ExperimentDesign,
        start_date: date,
        adherence_logs: List[AdherenceLog],
        current_date: Optional[date] = None,
    ) -> ExperimentProgress:
        """
        Get current progress of the experiment.

        Args:
            design: The experiment design
            start_date: When the experiment started
            adherence_logs: All adherence logs recorded
            current_date: Current date (defaults to today)

        Returns:
            ExperimentProgress with current state
        """
        current_date = current_date or date.today()
        phase, phase_day = self.get_current_phase(design, start_date, current_date)

        # Determine phase total days
        phase_days_map = {
            ExperimentPhase.BASELINE: design.baseline_days,
            ExperimentPhase.INTERVENTION: design.intervention_days,
            ExperimentPhase.WASHOUT: design.washout_days,
            ExperimentPhase.ANALYSIS: 0,
        }
        phase_total = phase_days_map.get(phase, 0)

        overall_day = (current_date - start_date).days + 1
        days_remaining = max(0, design.total_days - overall_day + 1)

        # Adherence rate (intervention phase only)
        intervention_logs = [
            log for log in adherence_logs
            if self._is_intervention_date(design, start_date, log.log_date)
        ]
        adherence_rate = (
            sum(1 for log in intervention_logs if log.adhered) / len(intervention_logs)
            if intervention_logs else 0.0
        )

        # Adherence streak
        streak = 0
        for log in sorted(adherence_logs, key=lambda l: l.log_date, reverse=True):
            if log.adhered:
                streak += 1
            else:
                break

        is_on_track = adherence_rate >= design.success_criteria.min_adherence

        phase_progress = (phase_day / phase_total * 100) if phase_total > 0 else 0.0

        return ExperimentProgress(
            current_phase=phase,
            phase_day=phase_day,
            phase_total_days=phase_total,
            overall_day=overall_day,
            overall_total_days=design.total_days,
            days_remaining=days_remaining,
            adherence_rate=round(adherence_rate, 2),
            adherence_streak=streak,
            is_on_track=is_on_track,
            phase_progress_pct=round(phase_progress, 1),
        )

    def check_early_stop(
        self,
        design: ExperimentDesign,
        baseline_values: List[float],
        intervention_values: List[float],
    ) -> EarlyStopSignal:
        """
        Check if the experiment can be stopped early.

        Early stopping rules:
        1. Clear positive signal: effect >> threshold with p < 0.01
        2. Futility: very high p-value suggesting no effect
        3. Not enough data: always continue

        Args:
            design: The experiment design
            baseline_values: Metric values during baseline
            intervention_values: Metric values during intervention so far

        Returns:
            EarlyStopSignal with recommendation
        """
        if len(intervention_values) < EARLY_STOP_MIN_DAYS:
            return EarlyStopSignal(
                should_stop=False,
                reason="Insufficient intervention data for early assessment",
                current_effect_size=0.0,
                current_p_value=1.0,
                confidence=0.0,
            )

        if len(baseline_values) < 5:
            return EarlyStopSignal(
                should_stop=False,
                reason="Insufficient baseline data",
                current_effect_size=0.0,
                current_p_value=1.0,
                confidence=0.0,
            )

        # Compute current effect
        bl = np.array(baseline_values, dtype=np.float64)
        iv = np.array(intervention_values, dtype=np.float64)

        pooled_std = np.sqrt(
            ((len(bl) - 1) * np.var(bl, ddof=1) + (len(iv) - 1) * np.var(iv, ddof=1))
            / (len(bl) + len(iv) - 2)
        )

        if pooled_std < 1e-10:
            pooled_std = 1e-10

        effect_size = abs(float(np.mean(iv) - np.mean(bl))) / pooled_std
        _, p_value = ttest_ind(bl, iv)
        p_value = float(p_value)

        # Rule 1: Clear positive signal
        required_effect = design.success_criteria.min_effect_size
        if (
            effect_size > required_effect * EARLY_STOP_EFFECT_MULTIPLIER
            and p_value < EARLY_STOP_P_THRESHOLD
        ):
            return EarlyStopSignal(
                should_stop=True,
                reason=f"Strong positive signal: effect={effect_size:.2f} (>{required_effect * EARLY_STOP_EFFECT_MULTIPLIER:.2f}), p={p_value:.4f}",
                current_effect_size=round(effect_size, 3),
                current_p_value=round(p_value, 4),
                confidence=round(1 - p_value, 3),
            )

        # Rule 2: Futility
        if (
            len(intervention_values) > design.intervention_days * 0.6
            and p_value > FUTILITY_P_THRESHOLD
            and effect_size < required_effect * 0.25
        ):
            return EarlyStopSignal(
                should_stop=True,
                reason=f"Futility: very small effect ({effect_size:.2f}) with high p-value ({p_value:.2f}) after {len(intervention_values)} days",
                current_effect_size=round(effect_size, 3),
                current_p_value=round(p_value, 4),
                confidence=round(1 - p_value, 3),
            )

        return EarlyStopSignal(
            should_stop=False,
            reason="Experiment should continue",
            current_effect_size=round(effect_size, 3),
            current_p_value=round(p_value, 4),
            confidence=round(1 - p_value, 3),
        )

    def analyze(
        self,
        design: ExperimentDesign,
        metric_data: Dict[str, Tuple[List[float], List[float]]],
        adherence_logs: List[AdherenceLog],
        confounders: Optional[List[str]] = None,
    ) -> ExperimentResult:
        """
        Run final analysis on a completed experiment.

        Args:
            design: The experiment design
            metric_data: Dict of metric_key → (baseline_values, intervention_values)
            adherence_logs: All adherence logs
            confounders: Any confounders noted during the experiment

        Returns:
            ExperimentResult with verdict and detailed results
        """
        criteria = design.success_criteria
        confounders = confounders or []

        # Analyze primary metric
        primary_key = criteria.primary_metric
        if primary_key not in metric_data:
            return ExperimentResult(
                verdict=Verdict.INSUFFICIENT_DATA,
                primary_result=_empty_metric_result(primary_key),
                secondary_results=[],
                overall_effect_size=0.0,
                overall_confidence=0.0,
                adherence_rate=0.0,
                met_adherence_requirement=False,
                met_effect_threshold=False,
                confounders_noted=confounders,
                summary="Primary metric data not available for analysis.",
            )

        bl, iv = metric_data[primary_key]
        primary_result = _analyze_metric(primary_key, bl, iv, criteria.direction)

        # Analyze secondary metrics
        secondary_results = []
        for metric in criteria.secondary_metrics:
            if metric in metric_data:
                bl_s, iv_s = metric_data[metric]
                secondary_results.append(
                    _analyze_metric(metric, bl_s, iv_s, criteria.direction)
                )

        # Adherence
        intervention_logs = [log for log in adherence_logs if log.adhered is not None]
        adherence_rate = (
            sum(1 for log in intervention_logs if log.adhered) / len(intervention_logs)
            if intervention_logs else 0.0
        )
        met_adherence = adherence_rate >= criteria.min_adherence

        # Effect threshold
        met_effect = (
            abs(primary_result.effect_size) >= criteria.min_effect_size
            and primary_result.significant
        )

        # Generate verdict
        verdict = _compute_verdict(
            primary_result, met_adherence, met_effect, criteria
        )

        summary = _generate_summary(
            verdict, primary_result, adherence_rate, met_adherence, confounders, design
        )

        return ExperimentResult(
            verdict=verdict,
            primary_result=primary_result,
            secondary_results=secondary_results,
            overall_effect_size=round(primary_result.effect_size, 3),
            overall_confidence=round(1 - primary_result.p_value, 3),
            adherence_rate=round(adherence_rate, 2),
            met_adherence_requirement=met_adherence,
            met_effect_threshold=met_effect,
            confounders_noted=confounders,
            summary=summary,
        )

    def _is_intervention_date(
        self,
        design: ExperimentDesign,
        start_date: date,
        check_date: date,
    ) -> bool:
        """Check if a date falls within the intervention phase."""
        elapsed = (check_date - start_date).days
        intervention_start = design.baseline_days
        intervention_end = intervention_start + design.intervention_days
        return intervention_start <= elapsed < intervention_end


# ── Analysis Helpers ────────────────────────────────────────────────


def _analyze_metric(
    metric: str,
    baseline_values: List[float],
    intervention_values: List[float],
    expected_direction: str,
) -> MetricResult:
    """Analyze a single metric comparing baseline vs intervention."""
    bl = np.array(baseline_values, dtype=np.float64)
    iv = np.array(intervention_values, dtype=np.float64)

    bl_mean = float(np.mean(bl))
    bl_std = float(np.std(bl, ddof=1)) if len(bl) > 1 else 0.0
    iv_mean = float(np.mean(iv))
    iv_std = float(np.std(iv, ddof=1)) if len(iv) > 1 else 0.0

    # Pooled std for Cohen's d
    n1, n2 = len(bl), len(iv)
    if n1 > 1 and n2 > 1:
        pooled_std = np.sqrt(
            ((n1 - 1) * np.var(bl, ddof=1) + (n2 - 1) * np.var(iv, ddof=1))
            / (n1 + n2 - 2)
        )
    else:
        pooled_std = max(bl_std, iv_std) or 1e-10

    if pooled_std < 1e-10:
        pooled_std = 1e-10

    effect_size = (iv_mean - bl_mean) / pooled_std

    # t-test
    if n1 >= 2 and n2 >= 2:
        _, p_value = ttest_ind(bl, iv)
        p_value = float(p_value)
    else:
        p_value = 1.0

    actual_direction = "increase" if iv_mean > bl_mean else "decrease"
    # Significant if p < 0.05 AND effect is in expected direction
    correct_direction = actual_direction == expected_direction
    significant = p_value < 0.05 and correct_direction

    return MetricResult(
        metric=metric,
        baseline_mean=round(bl_mean, 4),
        baseline_std=round(bl_std, 4),
        intervention_mean=round(iv_mean, 4),
        intervention_std=round(iv_std, 4),
        effect_size=round(effect_size, 4),
        p_value=round(p_value, 4),
        direction=actual_direction,
        significant=significant,
        n_baseline=n1,
        n_intervention=n2,
    )


def _empty_metric_result(metric: str) -> MetricResult:
    return MetricResult(
        metric=metric,
        baseline_mean=0.0,
        baseline_std=0.0,
        intervention_mean=0.0,
        intervention_std=0.0,
        effect_size=0.0,
        p_value=1.0,
        direction="increase",
        significant=False,
        n_baseline=0,
        n_intervention=0,
    )


def _compute_verdict(
    primary: MetricResult,
    met_adherence: bool,
    met_effect: bool,
    criteria: SuccessCriteria,
) -> Verdict:
    """Compute the experiment verdict from results."""
    if primary.n_baseline < 5 or primary.n_intervention < 5:
        return Verdict.INSUFFICIENT_DATA

    if not met_adherence:
        return Verdict.UNCLEAR

    if met_effect:
        return Verdict.HELPFUL

    if primary.p_value > 0.5:
        return Verdict.NOT_HELPFUL

    return Verdict.UNCLEAR


def _generate_summary(
    verdict: Verdict,
    primary: MetricResult,
    adherence_rate: float,
    met_adherence: bool,
    confounders: List[str],
    design: ExperimentDesign,
) -> str:
    """Generate a human-readable summary of the experiment."""
    parts = [f"Experiment: {design.hypothesis}"]

    if verdict == Verdict.HELPFUL:
        parts.append(
            f"Result: {design.intervention} appears helpful. "
            f"{primary.metric} changed by {primary.effect_size:.2f} std devs "
            f"(p={primary.p_value:.3f})."
        )
    elif verdict == Verdict.NOT_HELPFUL:
        parts.append(
            f"Result: {design.intervention} did not show a meaningful effect on "
            f"{primary.metric} (effect={primary.effect_size:.2f}, p={primary.p_value:.3f})."
        )
    elif verdict == Verdict.UNCLEAR:
        if not met_adherence:
            parts.append(
                f"Result: Inconclusive due to low adherence ({adherence_rate:.0%}). "
                f"Consider re-running with better adherence tracking."
            )
        else:
            parts.append(
                f"Result: Inconclusive. Some signal detected but not strong enough "
                f"(effect={primary.effect_size:.2f}, p={primary.p_value:.3f})."
            )
    else:
        parts.append("Result: Insufficient data to draw conclusions.")

    if confounders:
        parts.append(f"Confounders noted: {', '.join(confounders)}.")

    return " ".join(parts)
