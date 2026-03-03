"""
Regime Classifier - Phase 3.3

Identifies what health "regime" a user is in based on their current
metric signals. Regimes change interpretation of data:
- During illness, low HRV is expected, not alarming
- During travel, disrupted sleep is expected
- During high stress, baseline comparisons should be regime-aware

Classification is rule-based with fuzzy thresholds, not ML.
This keeps it auditable and deterministic per the platform philosophy.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Regime(str, Enum):
    """Health regimes the system can detect."""
    NORMAL = "normal"
    ILLNESS = "illness"
    TRAVEL = "travel"
    HIGH_STRESS = "high_stress"
    RECOVERY = "recovery"
    TRAINING_PEAK = "training_peak"
    MENSTRUAL_PHASE = "menstrual_phase"


# Weights for how much each signal contributes to regime classification.
# Higher = more indicative of that regime.
REGIME_RULES: Dict[Regime, List[Tuple[str, str, float, float]]] = {
    # (metric_key, condition, threshold, weight)
    # condition: "below_baseline_pct" = % below personal baseline
    #            "above_baseline_pct" = % above personal baseline
    #            "above_absolute" = absolute value check
    #            "below_absolute" = absolute value check
    Regime.ILLNESS: [
        ("resting_hr", "above_baseline_pct", 15.0, 0.3),      # Elevated RHR
        ("hrv_rmssd", "below_baseline_pct", 25.0, 0.3),       # Suppressed HRV
        ("sleep_duration", "above_baseline_pct", 15.0, 0.15),  # Sleeping more (body recovering)
        ("energy", "below_absolute", 2.0, 0.25),               # Very low energy self-report
    ],
    Regime.HIGH_STRESS: [
        ("hrv_rmssd", "below_baseline_pct", 20.0, 0.3),       # HRV suppression
        ("resting_hr", "above_baseline_pct", 10.0, 0.2),      # Elevated RHR
        ("stress", "above_absolute", 4.0, 0.3),               # High stress self-report
        ("sleep_duration", "below_baseline_pct", 15.0, 0.2),  # Less sleep
    ],
    Regime.RECOVERY: [
        ("hrv_rmssd", "above_baseline_pct", 10.0, 0.3),       # HRV recovering
        ("resting_hr", "below_baseline_pct", 5.0, 0.2),       # RHR dropping
        ("energy", "above_absolute", 3.5, 0.2),               # Good energy
        ("sleep_duration", "above_baseline_pct", 10.0, 0.3),  # Sleeping more
    ],
    Regime.TRAINING_PEAK: [
        ("resting_hr", "above_baseline_pct", 8.0, 0.25),      # Slightly elevated RHR
        ("hrv_rmssd", "below_baseline_pct", 15.0, 0.25),      # Moderate HRV suppression
        ("sleep_duration", "above_baseline_pct", 5.0, 0.2),   # Slightly more sleep
        ("energy", "above_absolute", 3.0, 0.3),               # Decent energy (distinguishes from illness)
    ],
    Regime.TRAVEL: [
        ("sleep_duration", "below_baseline_pct", 20.0, 0.35),  # Much less sleep
        ("hrv_rmssd", "below_baseline_pct", 15.0, 0.25),       # HRV disrupted
        ("resting_hr", "above_baseline_pct", 5.0, 0.15),       # Slightly elevated
        ("energy", "below_absolute", 3.0, 0.25),               # Low-moderate energy
    ],
}

# Minimum score for a regime to be detected
REGIME_THRESHOLD = 0.5


@dataclass(frozen=True)
class RegimeClassification:
    """Result of regime classification."""
    regime: Regime
    confidence: float  # 0-1
    contributing_signals: List[str]
    date: date


@dataclass(frozen=True)
class RegimePeriod:
    """A period of time under a specific regime."""
    regime: Regime
    start_date: date
    end_date: Optional[date]
    avg_confidence: float


class RegimeClassifier:
    """
    Classifies the user's current health regime from metric signals.

    Uses rule-based fuzzy matching against personal baselines.
    Deterministic and auditable per platform philosophy.
    """

    def classify(
        self,
        features: Dict[str, float],
        baselines: Dict[str, Tuple[float, float]],
    ) -> RegimeClassification:
        """
        Determine what regime the user is in.

        Args:
            features: Current metric values {"resting_hr": 72, "hrv_rmssd": 35, ...}
            baselines: Personal baselines {"resting_hr": (62, 3), "hrv_rmssd": (45, 8), ...}
                       as (center, spread) tuples.

        Returns:
            RegimeClassification with the most likely regime.
        """
        scores: Dict[Regime, Tuple[float, List[str]]] = {}

        for regime, rules in REGIME_RULES.items():
            score = 0.0
            contributing = []

            for metric_key, condition, threshold, weight in rules:
                if metric_key not in features:
                    continue

                value = features[metric_key]
                triggered = False

                if condition == "above_baseline_pct":
                    baseline = baselines.get(metric_key)
                    if baseline and baseline[0] > 0:
                        pct_above = ((value - baseline[0]) / baseline[0]) * 100
                        if pct_above >= threshold:
                            triggered = True
                elif condition == "below_baseline_pct":
                    baseline = baselines.get(metric_key)
                    if baseline and baseline[0] > 0:
                        pct_below = ((baseline[0] - value) / baseline[0]) * 100
                        if pct_below >= threshold:
                            triggered = True
                elif condition == "above_absolute":
                    if value >= threshold:
                        triggered = True
                elif condition == "below_absolute":
                    if value <= threshold:
                        triggered = True

                if triggered:
                    score += weight
                    contributing.append(metric_key)

            scores[regime] = (score, contributing)

        # Find the highest-scoring regime
        best_regime = Regime.NORMAL
        best_score = 0.0
        best_signals: List[str] = []

        for regime, (score, signals) in scores.items():
            if score > best_score and score >= REGIME_THRESHOLD:
                best_regime = regime
                best_score = score
                best_signals = signals

        return RegimeClassification(
            regime=best_regime,
            confidence=min(1.0, best_score),
            contributing_signals=best_signals,
            date=date.today(),
        )

    def should_suppress_insights(self, regime: Regime) -> bool:
        """Should insights be suppressed during this regime?"""
        # During illness and travel, normal insights may be misleading
        return regime in (Regime.ILLNESS, Regime.TRAVEL)

    def get_regime_context(self, regime: Regime) -> str:
        """Get human-readable context for a regime."""
        contexts = {
            Regime.NORMAL: "Your metrics are within your normal range.",
            Regime.ILLNESS: (
                "Your body appears to be fighting something. "
                "Elevated heart rate and suppressed HRV are expected during illness. "
                "Normal patterns will resume after recovery."
            ),
            Regime.TRAVEL: (
                "Travel disruption detected. Sleep and recovery metrics "
                "may be affected for 2-3 days. This is expected."
            ),
            Regime.HIGH_STRESS: (
                "Signs of elevated stress load detected. "
                "Your nervous system metrics suggest increased allostatic load."
            ),
            Regime.RECOVERY: (
                "Your body appears to be in a recovery phase. "
                "HRV is rising and resting heart rate is normalizing."
            ),
            Regime.TRAINING_PEAK: (
                "Your training load appears elevated. "
                "Some stress markers are expected during hard training blocks."
            ),
            Regime.MENSTRUAL_PHASE: (
                "Menstrual cycle phase may be influencing your metrics. "
                "This is a normal physiological variation."
            ),
        }
        return contexts.get(regime, "")

    def build_regime_timeline(
        self,
        classifications: List[RegimeClassification],
    ) -> List[RegimePeriod]:
        """
        Convert a series of daily classifications into regime periods.

        Groups consecutive days with the same regime into periods.
        """
        if not classifications:
            return []

        # Sort by date
        sorted_cls = sorted(classifications, key=lambda c: c.date)

        periods: List[RegimePeriod] = []
        current_regime = sorted_cls[0].regime
        current_start = sorted_cls[0].date
        confidences = [sorted_cls[0].confidence]

        for cls in sorted_cls[1:]:
            if cls.regime != current_regime:
                # End current period
                periods.append(RegimePeriod(
                    regime=current_regime,
                    start_date=current_start,
                    end_date=cls.date - timedelta(days=1),
                    avg_confidence=sum(confidences) / len(confidences),
                ))
                # Start new period
                current_regime = cls.regime
                current_start = cls.date
                confidences = [cls.confidence]
            else:
                confidences.append(cls.confidence)

        # Close the last period
        periods.append(RegimePeriod(
            regime=current_regime,
            start_date=current_start,
            end_date=sorted_cls[-1].date,
            avg_confidence=sum(confidences) / len(confidences),
        ))

        return periods
