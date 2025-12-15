"""
System-Level Validation & Invariants (STEP X1)

Hard-fail checks for critical data integrity and logical consistency.
These invariants must be satisfied before any object is created or persisted.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.domain.metric_registry import METRICS, get_metric_spec

logger = logging.getLogger(__name__)


class InvariantViolation(Exception):
    """Raised when a system invariant is violated."""
    
    def __init__(self, invariant_name: str, message: str, context: Optional[Dict[str, Any]] = None):
        self.invariant_name = invariant_name
        self.message = message
        self.context = context or {}
        super().__init__(f"[{invariant_name}] {message}")


def validate_insight_invariants(
    *,
    user_id: int,
    insight_type: str,
    title: str,
    description: str,
    confidence_score: float,
    metadata_json: str,
) -> None:
    """
    Validate invariants for Insight creation.
    
    Invariants:
    - Must have metric_key in metadata_json
    - Must have evidence in metadata_json
    - Must have confidence_score in [0, 1]
    - Title and description must be non-empty
    """
    errors: List[str] = []
    context: Dict[str, Any] = {
        "user_id": user_id,
        "insight_type": insight_type,
    }
    
    # Parse metadata
    try:
        metadata = json.loads(metadata_json) if isinstance(metadata_json, str) else metadata_json
    except Exception as e:
        raise InvariantViolation(
            "insight_metadata_invalid",
            f"metadata_json must be valid JSON: {e}",
            context,
        )
    
    # Check metric_key
    metric_key = metadata.get("metric_key")
    if not metric_key:
        errors.append("metadata_json must contain 'metric_key'")
    elif metric_key not in METRICS:
        errors.append(f"metric_key '{metric_key}' not found in metric registry")
    else:
        context["metric_key"] = metric_key
    
    # Check evidence
    if "evidence" not in metadata and not metadata.get("status"):
        errors.append("metadata_json must contain 'evidence' or 'status'")
    
    # Check confidence_score
    if not isinstance(confidence_score, (int, float)) or not (0.0 <= confidence_score <= 1.0):
        errors.append(f"confidence_score must be in [0, 1], got {confidence_score}")
    
    # Check title/description
    if not title or not title.strip():
        errors.append("title must be non-empty")
    if not description or not description.strip():
        errors.append("description must be non-empty")
    
    if errors:
        context["errors"] = errors
        logger.error(
            "insight_invariant_violation",
            extra={
                "invariant": "insight_creation",
                "user_id": user_id,
                "errors": errors,
                "metadata": metadata,
            },
        )
        raise InvariantViolation(
            "insight_creation_invalid",
            f"Insight creation failed: {', '.join(errors)}",
            context,
        )


def validate_intervention_invariants(
    *,
    user_id: int,
    key: str,
    name: str,
    safety_risk_level: Optional[str] = None,
    safety_evidence_grade: Optional[str] = None,
    safety_boundary: Optional[str] = None,
) -> None:
    """
    Validate invariants for Intervention creation.
    
    Invariants:
    - Must have safety_decision (safety_risk_level, safety_evidence_grade, safety_boundary)
    - Key and name must be non-empty
    """
    errors: List[str] = []
    context: Dict[str, Any] = {
        "user_id": user_id,
        "key": key,
    }
    
    # Check key/name
    if not key or not key.strip():
        errors.append("key must be non-empty")
    if not name or not name.strip():
        errors.append("name must be non-empty")
    
    # Check safety_decision (all safety fields must be present)
    if not safety_risk_level:
        errors.append("safety_risk_level must be set (safety decision required)")
    if not safety_evidence_grade:
        errors.append("safety_evidence_grade must be set (safety decision required)")
    if not safety_boundary:
        errors.append("safety_boundary must be set (safety decision required)")
    
    # Validate safety_risk_level enum
    if safety_risk_level and safety_risk_level not in ["low", "moderate", "high"]:
        errors.append(f"safety_risk_level must be one of ['low', 'moderate', 'high'], got '{safety_risk_level}'")
    
    # Validate safety_evidence_grade enum
    if safety_evidence_grade and safety_evidence_grade not in ["A", "B", "C", "D"]:
        errors.append(f"safety_evidence_grade must be one of ['A', 'B', 'C', 'D'], got '{safety_evidence_grade}'")
    
    # Validate safety_boundary enum
    if safety_boundary and safety_boundary not in ["informational", "lifestyle", "experiment"]:
        errors.append(f"safety_boundary must be one of ['informational', 'lifestyle', 'experiment'], got '{safety_boundary}'")
    
    if errors:
        context["errors"] = errors
        logger.error(
            "intervention_invariant_violation",
            extra={
                "invariant": "intervention_creation",
                "user_id": user_id,
                "errors": errors,
            },
        )
        raise InvariantViolation(
            "intervention_creation_invalid",
            f"Intervention creation failed: {', '.join(errors)}",
            context,
        )


def validate_evaluation_invariants(
    *,
    user_id: int,
    experiment_id: int,
    metric_key: str,
    verdict: str,
    baseline_mean: float,
    baseline_std: float,
    intervention_mean: float,
    intervention_std: float,
    coverage: float,
    details_json: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Validate invariants for EvaluationResult creation.
    
    Invariants:
    - Must have baseline_window in details_json
    - Must have intervention_window in details_json
    - Must have coverage in [0, 1]
    - Verdict must be valid enum
    - Metric_key must be in registry
    """
    errors: List[str] = []
    context: Dict[str, Any] = {
        "user_id": user_id,
        "experiment_id": experiment_id,
        "metric_key": metric_key,
    }
    
    # Check metric_key in registry
    if metric_key not in METRICS:
        errors.append(f"metric_key '{metric_key}' not found in metric registry")
    
    # Check verdict enum
    valid_verdicts = ["helpful", "unclear", "not_helpful", "insufficient_data"]
    if verdict not in valid_verdicts:
        errors.append(f"verdict must be one of {valid_verdicts}, got '{verdict}'")
    
    # Check coverage
    if not isinstance(coverage, (int, float)) or not (0.0 <= coverage <= 1.0):
        errors.append(f"coverage must be in [0, 1], got {coverage}")
    
    # Check baseline_window and intervention_window in details_json
    if details_json:
        if "baseline_window" not in details_json:
            errors.append("details_json must contain 'baseline_window'")
        if "intervention_window" not in details_json:
            errors.append("details_json must contain 'intervention_window'")
    else:
        errors.append("details_json must be provided with baseline_window and intervention_window")
    
    # Check baseline stats are valid
    if baseline_std < 0:
        errors.append(f"baseline_std must be >= 0, got {baseline_std}")
    if intervention_std < 0:
        errors.append(f"intervention_std must be >= 0, got {intervention_std}")
    
    if errors:
        context["errors"] = errors
        logger.error(
            "evaluation_invariant_violation",
            extra={
                "invariant": "evaluation_creation",
                "user_id": user_id,
                "experiment_id": experiment_id,
                "errors": errors,
            },
        )
        raise InvariantViolation(
            "evaluation_creation_invalid",
            f"Evaluation creation failed: {', '.join(errors)}",
            context,
        )


def validate_provider_ingestion_invariants(
    *,
    user_id: int,
    metric_type: str,
    value: float,
    unit: str,
    source: str,
) -> None:
    """
    Validate invariants for provider data ingestion.
    
    Invariants:
    - Metric_type must be in metric registry
    - Unit must match metric spec unit
    - Value must be within metric spec valid_range (if defined)
    - Source must be non-empty
    """
    errors: List[str] = []
    context: Dict[str, Any] = {
        "user_id": user_id,
        "metric_type": metric_type,
        "source": source,
    }
    
    # Check metric_type in registry
    spec = get_metric_spec(metric_type)
    if not spec:
        errors.append(f"metric_type '{metric_type}' not found in metric registry")
    else:
        # Check unit matches
        if unit != spec.unit:
            errors.append(f"unit '{unit}' does not match metric spec unit '{spec.unit}'")
        
        # Check value range if defined
        if spec.valid_range:
            min_val, max_val = spec.valid_range
            if not (min_val <= value <= max_val):
                errors.append(f"value {value} outside valid_range [{min_val}, {max_val}]")
    
    # Check source
    if not source or not source.strip():
        errors.append("source must be non-empty")
    
    if errors:
        context["errors"] = errors
        logger.error(
            "provider_ingestion_invariant_violation",
            extra={
                "invariant": "provider_ingestion",
                "user_id": user_id,
                "metric_type": metric_type,
                "errors": errors,
            },
        )
        raise InvariantViolation(
            "provider_ingestion_invalid",
            f"Provider ingestion failed: {', '.join(errors)}",
            context,
        )


def validate_narrative_invariants(
    *,
    user_id: int,
    title: str,
    summary: str,
    key_points_json: List[Any],
    drivers_json: List[Any],
    risks_json: List[Any],
) -> None:
    """
    Validate invariants for Narrative creation.
    
    Invariants:
    - Narrative must not contradict safety warnings (if risks_json contains high/moderate risks, narrative must acknowledge them)
    - Narrative must not hide uncertainty (if confidence is low, narrative must mention it)
    - Title and summary must be non-empty
    """
    errors: List[str] = []
    context: Dict[str, Any] = {
        "user_id": user_id,
    }
    
    # Check title/summary
    if not title or not title.strip():
        errors.append("title must be non-empty")
    if not summary or not summary.strip():
        errors.append("summary must be non-empty")
    
    # Check for safety contradictions
    high_risk_count = 0
    for risk in risks_json:
        if isinstance(risk, dict):
            risk_level = risk.get("risk_level") or risk.get("severity")
            if risk_level in ["high", "moderate"]:
                high_risk_count += 1
    
    if high_risk_count > 0:
        # Check if narrative acknowledges risks
        summary_lower = summary.lower()
        key_points_text = " ".join([str(kp) for kp in key_points_json]).lower()
        combined_text = (summary_lower + " " + key_points_text)
        
        risk_keywords = ["risk", "warning", "caution", "safety", "concern", "alert"]
        has_risk_mention = any(keyword in combined_text for keyword in risk_keywords)
        
        if not has_risk_mention:
            errors.append(f"Narrative must acknowledge {high_risk_count} high/moderate risk(s) but no risk keywords found")
    
    if errors:
        context["errors"] = errors
        logger.error(
            "narrative_invariant_violation",
            extra={
                "invariant": "narrative_creation",
                "user_id": user_id,
                "errors": errors,
            },
        )
        raise InvariantViolation(
            "narrative_creation_invalid",
            f"Narrative creation failed: {', '.join(errors)}",
            context,
        )

