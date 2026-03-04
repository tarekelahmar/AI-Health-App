"""
Deterministic Explanation Generator

Translates statistical evidence into human-readable explanations
without requiring an LLM. Respects claim policies and governance
constraints at every level.

This module is the primary explanation pathway. LLM translation
(when enabled) can override these explanations, but the deterministic
generator ensures every insight always has readable text.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.domain.claims import EvidenceGrade, ClaimPolicy
from app.domain.metrics.registry import METRIC_REGISTRY
from app.domain.health_domains import HEALTH_DOMAINS, HealthDomainKey
from app.engine.governance.claim_policy import (
    get_policy as get_governance_policy,
    validate_language as validate_governance_language,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_display_name(metric_key: str) -> str:
    """Get human-readable metric name from registry, or title-case the key."""
    spec = METRIC_REGISTRY.get(metric_key)
    if spec:
        return spec.display_name
    # Fallback: convert snake_case to Title Case
    return metric_key.replace("_", " ").title()


def _get_unit(metric_key: str) -> str:
    """Get unit label for a metric. Returns empty string if unknown."""
    spec = METRIC_REGISTRY.get(metric_key)
    if spec:
        unit = spec.unit
        # Make units more readable
        unit_labels = {
            "minutes": "min",
            "percent": "%",
            "bpm": "bpm",
            "ms": "ms",
            "count": "steps",
            "score_1_5": "/5",
        }
        return unit_labels.get(unit, unit)
    return ""


def _get_domain_display_name(domain_key: Optional[str]) -> Optional[str]:
    """Get human-readable domain name."""
    if not domain_key:
        return None
    try:
        dk = HealthDomainKey(domain_key)
        domain = HEALTH_DOMAINS.get(dk)
        if domain:
            return domain.display_name
    except (ValueError, KeyError):
        pass
    return domain_key.replace("_", " ").title()


def _fmt(value: Optional[float], decimals: int = 1) -> str:
    """Format a numeric value, returning '—' for None."""
    if value is None:
        return "—"
    if isinstance(value, int) or value == int(value):
        return str(int(value))
    return f"{value:.{decimals}f}"


def _direction_word(direction: Optional[str], grade: EvidenceGrade) -> str:
    """
    Get a claim-policy-compliant directional verb phrase.

    The language naturally incorporates words that satisfy governance phrase
    requirements at various levels (e.g., "has changed", "shows", "appears to").
    """
    d = (direction or "").lower()

    if d in ("up", "positive", "increase", "improved"):
        if grade == EvidenceGrade.A:
            return "has changed, showing an increase in"
        elif grade == EvidenceGrade.B:
            return "appears to have changed, suggesting an increase in"
        elif grade == EvidenceGrade.C:
            return "might have changed, possibly showing an increase in"
        else:
            return "might suggest a possible increase in"
    elif d in ("down", "negative", "decrease", "declined"):
        if grade == EvidenceGrade.A:
            return "has changed, showing a decrease in"
        elif grade == EvidenceGrade.B:
            return "appears to have changed, suggesting a decrease in"
        elif grade == EvidenceGrade.C:
            return "might have changed, possibly showing a decrease in"
        else:
            return "might suggest a possible decrease in"
    else:
        # Neutral / unknown direction
        if grade in (EvidenceGrade.A, EvidenceGrade.B):
            return "has changed compared to"
        else:
            return "might suggest changes in"


# ---------------------------------------------------------------------------
# Per-type explanation builders
# ---------------------------------------------------------------------------

def _explain_change(
    display_name: str,
    unit: str,
    evidence: Dict[str, Any],
    metadata: Dict[str, Any],
    grade: EvidenceGrade,
) -> str:
    """Build explanation for a change-type insight."""
    direction = metadata.get("direction") or evidence.get("direction")
    verb_phrase = _direction_word(direction, grade)

    baseline_mean = evidence.get("baseline_mean")
    recent_mean = evidence.get("recent_mean")
    z_score = evidence.get("z_score")
    n_points = evidence.get("n_points") or evidence.get("sample_size")

    parts = [f"Your {display_name} {verb_phrase} your personal baseline."]

    # Add numeric context if we have it
    if recent_mean is not None and baseline_mean is not None:
        unit_suffix = f" {unit}" if unit else ""
        parts.append(
            f"Recent values averaged {_fmt(recent_mean)}{unit_suffix}, "
            f"compared to a baseline of {_fmt(baseline_mean)}{unit_suffix}."
        )
    elif recent_mean is not None:
        unit_suffix = f" {unit}" if unit else ""
        parts.append(f"Recent values averaged {_fmt(recent_mean)}{unit_suffix}.")

    # Z-score context for informed users (keep it readable)
    if z_score is not None:
        abs_z = abs(z_score)
        if abs_z >= 3:
            parts.append("This is a large deviation from your typical range.")
        elif abs_z >= 2:
            parts.append("This is a notable deviation from your typical range.")
        elif abs_z >= 1:
            parts.append("This is a moderate shift from your typical range.")

    if n_points is not None:
        parts.append(f"Based on {_fmt(n_points, 0)} data points.")

    return " ".join(parts)


def _explain_trend(
    display_name: str,
    unit: str,
    evidence: Dict[str, Any],
    metadata: Dict[str, Any],
    grade: EvidenceGrade,
) -> str:
    """Build explanation for a trend-type insight."""
    direction = metadata.get("direction") or evidence.get("direction")
    verb_phrase = _direction_word(direction, grade)

    slope = evidence.get("slope_per_day")
    window_days = evidence.get("window_days")
    n_points = evidence.get("n_points") or evidence.get("sample_size")
    days_consistent = evidence.get("days_consistent")

    parts = [f"Your {display_name} {verb_phrase} your recent values."]

    if slope is not None and window_days is not None:
        unit_suffix = f" {unit}" if unit else ""
        parts.append(
            f"Over the past {_fmt(window_days, 0)} days, "
            f"it changed by approximately {_fmt(abs(slope), 2)}{unit_suffix} per day."
        )
    elif window_days is not None:
        parts.append(f"This pattern was observed over {_fmt(window_days, 0)} days.")

    if days_consistent is not None and days_consistent > 1:
        parts.append(f"This trend has been consistent for {_fmt(days_consistent, 0)} days.")

    if n_points is not None:
        parts.append(f"Based on {_fmt(n_points, 0)} data points.")

    return " ".join(parts)


def _explain_instability(
    display_name: str,
    unit: str,
    evidence: Dict[str, Any],
    metadata: Dict[str, Any],
    grade: EvidenceGrade,
) -> str:
    """Build explanation for an instability-type insight."""
    ratio = evidence.get("instability_ratio")
    recent_std = evidence.get("recent_std")
    baseline_std = evidence.get("baseline_std")

    if grade in (EvidenceGrade.A, EvidenceGrade.B):
        opener = f"Your {display_name} shows increased day-to-day variability."
    else:
        opener = f"Your {display_name} might be showing increased variability."

    parts = [opener]

    if ratio is not None:
        parts.append(
            f"Recent variation is {_fmt(ratio)}x your usual baseline variation."
        )
    elif recent_std is not None and baseline_std is not None:
        parts.append(
            f"Recent standard deviation is {_fmt(recent_std)} vs baseline of {_fmt(baseline_std)}."
        )

    parts.append(
        "Higher variability can indicate disrupted patterns "
        "or sensitivity to changing conditions."
    )

    return " ".join(parts)


def _explain_safety(
    display_name: str,
    evidence: Dict[str, Any],
    metadata: Dict[str, Any],
) -> str:
    """Build explanation for a safety-type insight."""
    triggers_count = evidence.get("triggers_count", 0)

    parts = [
        f"A safety-related pattern was detected in your {display_name}.",
    ]

    if triggers_count and triggers_count > 0:
        parts.append(
            f"{int(triggers_count)} safety trigger(s) were identified."
        )

    parts.append(
        "This does not necessarily indicate a medical issue, "
        "but you may want to review the data and consider "
        "discussing it with a healthcare provider."
    )

    return " ".join(parts)


def _explain_default(
    display_name: str,
    unit: str,
    evidence: Dict[str, Any],
    metadata: Dict[str, Any],
    grade: EvidenceGrade,
) -> str:
    """Fallback explanation for unknown insight types."""
    direction = metadata.get("direction") or evidence.get("direction")
    verb_phrase = _direction_word(direction, grade)

    parts = [f"A pattern was detected: your {display_name} {verb_phrase} recent values."]

    baseline_mean = evidence.get("baseline_mean")
    recent_mean = evidence.get("recent_mean")
    if recent_mean is not None and baseline_mean is not None:
        unit_suffix = f" {unit}" if unit else ""
        parts.append(
            f"Recent average: {_fmt(recent_mean)}{unit_suffix} "
            f"(baseline: {_fmt(baseline_mean)}{unit_suffix})."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Uncertainty & Next Step generators
# ---------------------------------------------------------------------------

def _generate_uncertainty(
    evidence: Dict[str, Any],
    grade: EvidenceGrade,
    governance_claim_level: int,
) -> str:
    """Generate an uncertainty statement based on evidence quality."""
    n_points = evidence.get("n_points") or evidence.get("sample_size")
    coverage = evidence.get("coverage")
    window_days = evidence.get("window_days")

    # Base uncertainty by grade
    if grade == EvidenceGrade.A:
        base = "This finding is based on consistent data with high confidence."
    elif grade == EvidenceGrade.B:
        base = "This pattern is based on a moderate amount of data. Further observation may strengthen or weaken this finding."
    elif grade == EvidenceGrade.C:
        base = "This observation is based on limited data. The pattern may change as more data is collected."
    else:  # Grade D
        base = "This is a preliminary observation based on very limited data. Confidence is low and the pattern may not persist."

    # Add coverage context if significantly low
    parts = [base]
    if coverage is not None and coverage < 0.5 and window_days is not None:
        pct = int(coverage * 100)
        parts.append(
            f"Data coverage for this period was {pct}%, which limits the reliability of this finding."
        )

    return " ".join(parts)


def _generate_next_step(
    insight_type: str,
    governance_claim_level: int,
) -> str:
    """Generate a suggested next step based on the governance claim level."""
    # Safety always gets the same recommendation
    if insight_type == "safety":
        return "Please consult a healthcare professional about this finding."

    # Use governance policy's allowed actions to guide the recommendation
    try:
        policy = get_governance_policy(governance_claim_level)
        allowed = policy.allowed_actions
    except (ValueError, KeyError):
        allowed = ["monitor"]

    if "continue_protocol" in allowed:
        return (
            "This pattern has been consistently observed. "
            "Review your current health protocols related to this metric."
        )
    elif "suggest_experiment" in allowed:
        return (
            "Consider setting up a tracked experiment to test whether "
            "a specific change affects this metric."
        )
    else:
        # Default: monitor only
        return (
            "Continue tracking this metric. More data will help "
            "confirm or dismiss this pattern."
        )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_deterministic_explanation(
    *,
    metric_key: str,
    insight_type: str,
    evidence: Dict[str, Any],
    metadata: Dict[str, Any],
    confidence: float,
    evidence_grade: EvidenceGrade,
    claim_policy: ClaimPolicy,
    governance_claim_level: int,
    domain_key: Optional[str] = None,
) -> Dict[str, str]:
    """
    Generate a human-readable explanation for an insight, deterministically.

    Returns a dict with keys: "explanation", "uncertainty", "suggested_next_step".
    All text is guaranteed to be claim-policy-compliant.
    """
    display_name = _get_display_name(metric_key)
    unit = _get_unit(metric_key)

    # Select explanation builder by insight type
    itype = (insight_type or "").lower()

    if itype == "change":
        explanation = _explain_change(display_name, unit, evidence, metadata, evidence_grade)
    elif itype == "trend":
        explanation = _explain_trend(display_name, unit, evidence, metadata, evidence_grade)
    elif itype in ("instability", "volatility"):
        explanation = _explain_instability(display_name, unit, evidence, metadata, evidence_grade)
    elif itype == "safety":
        explanation = _explain_safety(display_name, evidence, metadata)
    else:
        explanation = _explain_default(display_name, unit, evidence, metadata, evidence_grade)

    uncertainty = _generate_uncertainty(evidence, evidence_grade, governance_claim_level)
    suggested_next_step = _generate_next_step(itype, governance_claim_level)

    # --- Fail-closed validation ---
    # Check explanation text against governance forbidden phrases only.
    # Note: governance must_use_phrases are designed for insight titles/summaries,
    # not for detailed explanatory text — so we validate only forbidden words here.
    clamped_level = max(1, min(5, governance_claim_level))
    try:
        policy = get_governance_policy(clamped_level)
        combined_text = f"{explanation} {uncertainty} {suggested_next_step}".lower()
        violations = []
        for forbidden in policy.must_not_use_phrases:
            if forbidden.lower() in combined_text:
                violations.append(f"Must not use: '{forbidden}'")
        if violations:
            logger.warning(
                "explanation_generator_governance_violation",
                extra={
                    "metric_key": metric_key,
                    "insight_type": insight_type,
                    "claim_level": clamped_level,
                    "violations": violations,
                },
            )
            # Fall back to maximally conservative language
            explanation = (
                f"A pattern was detected in your {display_name}. "
                "Continue monitoring for more clarity."
            )
            uncertainty = (
                "This is a preliminary observation. "
                "More data is needed to draw conclusions."
            )
    except Exception as e:
        logger.error("explanation_generator_validation_error", extra={"error": str(e)})
        explanation = (
            f"A pattern was detected in your {display_name}. "
            "Continue monitoring for more clarity."
        )
        uncertainty = (
            "This is a preliminary observation. "
            "More data is needed to draw conclusions."
        )

    return {
        "explanation": explanation,
        "uncertainty": uncertainty,
        "suggested_next_step": suggested_next_step,
    }
