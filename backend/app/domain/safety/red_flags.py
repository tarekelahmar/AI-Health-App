from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any


@dataclass(frozen=True)
class RedFlagRule:
    key: str
    metric_key: Optional[str]           # None means "non-metric" (e.g., symptom)
    kind: str                           # "metric" | "symptom" | "lab"
    condition: str                      # "lt" | "gt" | "eq" | "in"
    threshold: Any
    message: str
    severity: str                       # "urgent" | "high" | "medium"
    action: str                         # "seek_care_now" | "contact_doctor" | "monitor"
    evidence: Dict[str, Any]


# NOTE: keep MVP focused. Expand rules over time.
RED_FLAG_RULES: List[RedFlagRule] = [
    # --- VITALS / WEARABLES ---
    RedFlagRule(
        key="sleep_very_low",
        metric_key="sleep_duration",
        kind="metric",
        condition="lt",
        threshold=240,  # < 4h
        message="Very low sleep duration detected (under 4 hours). If this is persistent or severe, consider medical advice.",
        severity="high",
        action="contact_doctor",
        evidence={"threshold": 240, "unit": "minutes"},
    ),
    RedFlagRule(
        key="resting_hr_high",
        metric_key="resting_hr",
        kind="metric",
        condition="gt",
        threshold=110,
        message="High resting heart rate detected (>110 bpm). If you feel unwell (chest pain, fainting, shortness of breath), seek urgent care.",
        severity="urgent",
        action="seek_care_now",
        evidence={"threshold": 110, "unit": "bpm"},
    ),
    RedFlagRule(
        key="hrv_very_low",
        metric_key="hrv_rmssd",
        kind="metric",
        condition="lt",
        threshold=15,
        message="Very low HRV detected. If combined with severe symptoms or illness, consider medical advice.",
        severity="medium",
        action="monitor",
        evidence={"threshold": 15, "unit": "ms"},
    ),

    # --- LABS (examples) ---
    RedFlagRule(
        key="glucose_very_high",
        metric_key="glucose_mgdl",
        kind="lab",
        condition="gt",
        threshold=300,
        message="Very high glucose detected. This can be dangerous. Seek medical care urgently, especially if symptomatic.",
        severity="urgent",
        action="seek_care_now",
        evidence={"threshold": 300, "unit": "mg/dL"},
    ),
    RedFlagRule(
        key="vitd_very_low",
        metric_key="vitamin_d_25oh",
        kind="lab",
        condition="lt",
        threshold=10,
        message="Very low vitamin D detected. Consider discussing supplementation and causes with a clinician.",
        severity="medium",
        action="contact_doctor",
        evidence={"threshold": 10, "unit": "ng/mL"},
    ),

    # --- SUBJECTIVE / SYMPTOMS (from daily check-in / symptom logs) ---
    RedFlagRule(
        key="severe_mood_crisis",
        metric_key=None,
        kind="symptom",
        condition="in",
        threshold=["suicidal_ideation", "self_harm_thoughts"],
        message="If you are in immediate danger or thinking about self-harm, seek urgent help now. Contact emergency services or a local crisis line.",
        severity="urgent",
        action="seek_care_now",
        evidence={"tags": ["suicidal_ideation", "self_harm_thoughts"]},
    ),
]


def _compare(condition: str, value: Any, threshold: Any) -> bool:
    if value is None:
        return False
    if condition == "lt":
        return float(value) < float(threshold)
    if condition == "gt":
        return float(value) > float(threshold)
    if condition == "eq":
        return value == threshold
    if condition == "in":
        # threshold is list; value may be list or str
        if isinstance(value, list):
            return any(v in threshold for v in value)
        return value in threshold
    return False


def evaluate_red_flags(
    *,
    latest_metrics: Dict[str, float],
    symptom_tags: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Returns list of triggered red flags as plain dicts (safe to JSON serialize).
    """
    triggered: List[Dict[str, Any]] = []
    symptom_tags = symptom_tags or []

    for rule in RED_FLAG_RULES:
        if rule.kind in ("metric", "lab"):
            v = latest_metrics.get(rule.metric_key or "")
            if _compare(rule.condition, v, rule.threshold):
                triggered.append(
                    {
                        "key": rule.key,
                        "metric_key": rule.metric_key,
                        "kind": rule.kind,
                        "severity": rule.severity,
                        "action": rule.action,
                        "message": rule.message,
                        "evidence": {**rule.evidence, "value": v},
                    }
                )
        elif rule.kind == "symptom":
            if _compare(rule.condition, symptom_tags, rule.threshold):
                triggered.append(
                    {
                        "key": rule.key,
                        "metric_key": None,
                        "kind": "symptom",
                        "severity": rule.severity,
                        "action": rule.action,
                        "message": rule.message,
                        "evidence": rule.evidence,
                    }
                )

    # Sort urgent first
    severity_order = {"urgent": 0, "high": 1, "medium": 2}
    triggered.sort(key=lambda x: severity_order.get(x["severity"], 9))
    return triggered

