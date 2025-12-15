import json
from app.api.schemas.insight import InsightResponse
from app.llm.client import translate_insight
from app.domain.claims import get_evidence_grade, get_claim_policy

INSIGHT_TYPE_TO_STATUS = {
    "change": "detected",
    "experiment": "evaluated",
    "safety": "detected",  # Safety insights are also "detected" status
}


def transform_insight(domain_insight) -> InsightResponse:
    """
    Converts Insight SQLAlchemy model → API response schema
    """
    # Parse metadata JSON safely
    metadata = {}
    if domain_insight.metadata_json:
        if isinstance(domain_insight.metadata_json, dict):
            metadata = domain_insight.metadata_json
        else:
            metadata = json.loads(domain_insight.metadata_json)

    metric_key = metadata.get("metric_key", "unknown")
    
    # Extract evidence fields - structure varies by insight type (change/trend/instability/safety)
    # Include all possible fields, they'll be None if not present
    evidence = {
        # Change detection fields
        "baseline_mean": metadata.get("baseline_mean"),
        "recent_mean": metadata.get("recent_mean"),
        "baseline_std": metadata.get("baseline_std"),
        "z_score": metadata.get("z_score"),
        "severity_std": metadata.get("severity_std"),  # legacy
        "days_consistent": metadata.get("days_consistent"),  # legacy
        # Trend fields
        "slope_per_day": metadata.get("slope_per_day"),
        # Instability fields
        "recent_std": metadata.get("recent_std"),
        "instability_ratio": metadata.get("instability_ratio"),
        # Experiment fields
        "followup_mean": metadata.get("followup_mean"),
        "delta": metadata.get("delta"),
        "effect_size": metadata.get("effect_size"),
        # Safety fields
        "triggers": metadata.get("triggers", []),  # List of red flag triggers
        # Common fields
        "type": metadata.get("type"),
        "window_days": metadata.get("window_days"),
        "n_points": metadata.get("n_points"),
        "direction": metadata.get("direction"),
        "strength": metadata.get("strength"),
    }
    
    status = INSIGHT_TYPE_TO_STATUS.get(
        domain_insight.insight_type,
        "suggested",
    )
    
    confidence = domain_insight.confidence_score or 0.0
    confidence = max(0.0, min(1.0, confidence))  # clamp

    # X3: Compute evidence grade
    sample_size = evidence.get("n_points", 0) or metadata.get("sample_size", 0) or 0
    coverage = metadata.get("coverage", 0.0) or 0.0
    effect_size = evidence.get("effect_size") or metadata.get("effect_size")
    p_value = metadata.get("p_value")
    
    evidence_grade = get_evidence_grade(
        confidence=confidence,
        sample_size=sample_size,
        coverage=coverage,
        effect_size=effect_size,
        p_value=p_value,
    )
    
    # Add evidence grade to evidence dict
    evidence["grade"] = evidence_grade.value
    evidence["strength"] = get_claim_policy(evidence_grade).strength.value

    resp = InsightResponse(
        id=domain_insight.id,
        created_at=domain_insight.generated_at,
        title=domain_insight.title,
        summary=domain_insight.description,
        metric_key=metric_key,
        confidence=confidence,
        status=status,
        evidence=evidence,
    )
    
    # Optionally add LLM translation (gated by environment variable)
    # X3: Pass claim policy to LLM
    claim_policy = get_claim_policy(evidence_grade)
    llm_output = translate_insight(
        {
            "title": resp.title,
            "summary": resp.summary,
            "metric_key": resp.metric_key,
            "confidence": resp.confidence,
            "status": resp.status,
            "evidence": resp.evidence,
        },
        evidence_grade=evidence_grade,
        claim_policy=claim_policy,
    )
    
    if llm_output:
        resp.explanation = llm_output.get("explanation")
        resp.uncertainty = llm_output.get("uncertainty")
        resp.suggested_next_step = llm_output.get("suggested_next_step")
    
    return resp

