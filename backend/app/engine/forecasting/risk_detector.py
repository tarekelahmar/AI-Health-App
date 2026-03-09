"""
Risk window detection for proactive health alerts.

Phase 5.2: Detects periods of elevated vulnerability before problems
manifest, using multi-signal risk scoring.

Risk Types:
  - illness_vulnerability: Immune suppression signals
  - burnout_trajectory: Sustained stress + declining recovery
  - overtraining_risk: Training load vs recovery imbalance
  - sleep_debt: Cumulative sleep deficit

Each risk type uses a weighted combination of relevant signals,
compared against personal baselines.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ── Data Classes ────────────────────────────────────────────────────


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"


@dataclass(frozen=True)
class ContributingFactor:
    """A signal contributing to risk assessment."""
    metric: str
    current_value: float
    baseline_value: float
    deviation_pct: float  # % deviation from baseline
    weight: float  # Contribution to overall risk score
    direction: str  # "above" or "below" baseline


@dataclass(frozen=True)
class RiskAssessment:
    """Complete risk assessment for a risk type."""
    risk_type: str
    risk_level: RiskLevel
    risk_score: float  # 0-1
    contributing_factors: List[ContributingFactor]
    description: str
    recommended_actions: List[str]
    days_in_current_state: int = 0


# ── Risk Configuration ──────────────────────────────────────────────

# Each risk type is defined by signals and their weights.
# direction: "below" means LOWER is worse, "above" means HIGHER is worse.

RISK_DEFINITIONS: Dict[str, List[Dict]] = {
    "illness_vulnerability": [
        {"metric": "hrv_rmssd_ms", "weight": 0.30, "direction": "below"},
        {"metric": "resting_heart_rate_bpm", "weight": 0.20, "direction": "above"},
        {"metric": "sleep_duration_minutes", "weight": 0.20, "direction": "below"},
        {"metric": "sleep_efficiency_pct", "weight": 0.15, "direction": "below"},
        {"metric": "respiratory_rate_brpm", "weight": 0.15, "direction": "above"},
    ],
    "burnout_trajectory": [
        {"metric": "hrv_rmssd_ms", "weight": 0.20, "direction": "below"},
        {"metric": "sleep_efficiency_pct", "weight": 0.15, "direction": "below"},
        {"metric": "subjective_energy", "weight": 0.25, "direction": "below"},
        {"metric": "subjective_stress", "weight": 0.25, "direction": "above"},
        {"metric": "resting_heart_rate_bpm", "weight": 0.15, "direction": "above"},
    ],
    "overtraining_risk": [
        {"metric": "hrv_rmssd_ms", "weight": 0.30, "direction": "below"},
        {"metric": "resting_heart_rate_bpm", "weight": 0.25, "direction": "above"},
        {"metric": "sleep_efficiency_pct", "weight": 0.20, "direction": "below"},
        {"metric": "subjective_energy", "weight": 0.25, "direction": "below"},
    ],
    "sleep_debt": [
        {"metric": "sleep_duration_minutes", "weight": 0.40, "direction": "below"},
        {"metric": "sleep_efficiency_pct", "weight": 0.25, "direction": "below"},
        {"metric": "subjective_energy", "weight": 0.20, "direction": "below"},
        {"metric": "hrv_rmssd_ms", "weight": 0.15, "direction": "below"},
    ],
}

# Thresholds for risk levels (score → level)
RISK_THRESHOLDS = {
    RiskLevel.LOW: 0.0,
    RiskLevel.MODERATE: 0.3,
    RiskLevel.ELEVATED: 0.55,
    RiskLevel.HIGH: 0.75,
}

# Recommended actions per risk type and level
RISK_ACTIONS: Dict[str, Dict[str, List[str]]] = {
    "illness_vulnerability": {
        "moderate": ["Prioritize sleep (aim for 8+ hours)", "Reduce training intensity"],
        "elevated": ["Avoid intense exercise", "Increase rest", "Consider immune-support supplements"],
        "high": ["Full rest day recommended", "Monitor symptoms closely", "Reduce social exposure if possible"],
    },
    "burnout_trajectory": {
        "moderate": ["Schedule recovery time", "Review workload"],
        "elevated": ["Reduce commitments", "Prioritize restorative activities", "Consider taking a day off"],
        "high": ["Immediate workload reduction needed", "Focus on sleep and recovery", "Consider professional support"],
    },
    "overtraining_risk": {
        "moderate": ["Reduce training volume by 20%", "Add extra rest day"],
        "elevated": ["Deload week recommended", "Focus on sleep quality", "Light activity only"],
        "high": ["Full rest recommended", "No high-intensity training", "Prioritize recovery protocols"],
    },
    "sleep_debt": {
        "moderate": ["Extend sleep opportunity by 30 minutes", "Avoid late caffeine"],
        "elevated": ["Target 9 hours sleep opportunity", "Limit screens before bed", "No evening alcohol"],
        "high": ["Nap if possible", "Extend sleep by 1+ hour", "Avoid demanding tasks", "Caffeine cutoff at noon"],
    },
}


# ── Risk Detector ───────────────────────────────────────────────────


class RiskWindowDetector:
    """
    Detects periods of elevated health risk from multi-signal analysis.

    Compares recent metric values against personal baselines to compute
    risk scores across predefined risk types.
    """

    def detect(
        self,
        risk_type: str,
        recent_values: Dict[str, float],
        baselines: Dict[str, Tuple[float, float]],  # metric → (center, spread)
        days_history: Optional[Dict[str, List[float]]] = None,
    ) -> RiskAssessment:
        """
        Assess risk level for a specific risk type.

        Args:
            risk_type: One of the defined risk types
            recent_values: Current/recent metric values
            baselines: Personal baselines as (center, spread) per metric
            days_history: Optional multi-day history for trend detection

        Returns:
            RiskAssessment with level, score, factors, and recommendations
        """
        if risk_type not in RISK_DEFINITIONS:
            raise ValueError(f"Unknown risk type: {risk_type}. Known: {list(RISK_DEFINITIONS.keys())}")

        signals = RISK_DEFINITIONS[risk_type]
        factors = []
        weighted_scores = []

        for signal_def in signals:
            metric = signal_def["metric"]
            weight = signal_def["weight"]
            direction = signal_def["direction"]

            current = recent_values.get(metric)
            baseline = baselines.get(metric)

            if current is None or baseline is None:
                continue

            center, spread = baseline
            if spread < 1e-10:
                spread = 1e-10

            # Compute deviation as z-score
            z = (current - center) / spread

            # Convert to risk contribution based on direction
            if direction == "below":
                # Lower is worse: negative z means higher risk
                risk_contribution = max(0.0, -z / 3.0)  # Normalize: 3 std = full risk
            else:
                # Higher is worse: positive z means higher risk
                risk_contribution = max(0.0, z / 3.0)

            risk_contribution = min(1.0, risk_contribution)

            # Apply trend bonus if multi-day history available
            if days_history and metric in days_history:
                trend_bonus = self._trend_risk(
                    days_history[metric], direction
                )
                risk_contribution = min(1.0, risk_contribution + trend_bonus * 0.2)

            weighted_scores.append(risk_contribution * weight)

            deviation_pct = ((current - center) / abs(center) * 100) if abs(center) > 1e-10 else 0.0

            factors.append(ContributingFactor(
                metric=metric,
                current_value=round(current, 2),
                baseline_value=round(center, 2),
                deviation_pct=round(deviation_pct, 1),
                weight=weight,
                direction="below" if current < center else "above",
            ))

        # Compute overall risk score
        if not weighted_scores:
            risk_score = 0.0
        else:
            # Normalize by total weight of available signals
            total_weight = sum(
                s["weight"] for s in signals
                if s["metric"] in recent_values and s["metric"] in baselines
            )
            risk_score = sum(weighted_scores) / total_weight if total_weight > 0 else 0.0

        risk_score = min(1.0, max(0.0, risk_score))
        risk_level = self._score_to_level(risk_score)

        # Sort factors by contribution (highest first)
        factors.sort(key=lambda f: abs(f.deviation_pct), reverse=True)

        return RiskAssessment(
            risk_type=risk_type,
            risk_level=risk_level,
            risk_score=round(risk_score, 3),
            contributing_factors=factors,
            description=self._describe_risk(risk_type, risk_level, factors),
            recommended_actions=self._get_actions(risk_type, risk_level),
        )

    def detect_all(
        self,
        recent_values: Dict[str, float],
        baselines: Dict[str, Tuple[float, float]],
        days_history: Optional[Dict[str, List[float]]] = None,
    ) -> List[RiskAssessment]:
        """Assess all risk types and return those above LOW."""
        assessments = []
        for risk_type in RISK_DEFINITIONS:
            assessment = self.detect(risk_type, recent_values, baselines, days_history)
            assessments.append(assessment)

        # Sort by risk score descending
        assessments.sort(key=lambda a: a.risk_score, reverse=True)
        return assessments

    def _trend_risk(self, history: List[float], direction: str) -> float:
        """
        Compute additional risk from trending in the wrong direction.

        Returns 0-1 bonus based on consistent adverse trend.
        """
        if len(history) < 3:
            return 0.0

        # Use last 5 days max
        recent = history[-5:]
        if len(recent) < 3:
            return 0.0

        # Simple slope via linear regression
        x = np.arange(len(recent), dtype=np.float64)
        y = np.array(recent, dtype=np.float64)
        if np.std(y) < 1e-10:
            return 0.0

        slope = float(np.polyfit(x, y, 1)[0])

        # Normalize slope by std of values
        normalized_slope = slope / (np.std(y) + 1e-10)

        # Check if trend is in the adverse direction
        if direction == "below" and normalized_slope < 0:
            # Decreasing when "below" = worse → adverse
            return min(1.0, abs(normalized_slope))
        elif direction == "above" and normalized_slope > 0:
            # Increasing when "above" = worse → adverse
            return min(1.0, abs(normalized_slope))

        return 0.0

    @staticmethod
    def _score_to_level(score: float) -> RiskLevel:
        if score >= RISK_THRESHOLDS[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        elif score >= RISK_THRESHOLDS[RiskLevel.ELEVATED]:
            return RiskLevel.ELEVATED
        elif score >= RISK_THRESHOLDS[RiskLevel.MODERATE]:
            return RiskLevel.MODERATE
        return RiskLevel.LOW

    @staticmethod
    def _describe_risk(
        risk_type: str,
        level: RiskLevel,
        factors: List[ContributingFactor],
    ) -> str:
        type_labels = {
            "illness_vulnerability": "illness vulnerability",
            "burnout_trajectory": "burnout risk",
            "overtraining_risk": "overtraining risk",
            "sleep_debt": "sleep debt",
        }
        label = type_labels.get(risk_type, risk_type)

        if level == RiskLevel.LOW:
            return f"Your {label} is currently low."

        top_factors = factors[:2]
        factor_parts = []
        for f in top_factors:
            pct = abs(f.deviation_pct)
            direction = "above" if f.deviation_pct > 0 else "below"
            factor_parts.append(f"{f.metric} is {pct:.0f}% {direction} baseline")

        factors_str = " and ".join(factor_parts)
        return f"Your {label} is {level.value}: {factors_str}."

    @staticmethod
    def _get_actions(risk_type: str, level: RiskLevel) -> List[str]:
        if level == RiskLevel.LOW:
            return []
        actions = RISK_ACTIONS.get(risk_type, {})
        return actions.get(level.value, [])
