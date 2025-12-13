import json
from app.api.schemas.insight import InsightResponse
from app.llm.client import translate_insight

INSIGHT_TYPE_TO_STATUS = {
    "change": "detected",
    "experiment": "evaluated",
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
    
    # Extract evidence fields - structure varies by insight type (change/trend/instability)
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
    llm_output = translate_insight({
        "title": resp.title,
        "summary": resp.summary,
        "metric_key": resp.metric_key,
        "confidence": resp.confidence,
        "status": resp.status,
        "evidence": resp.evidence,
    })
    
    if llm_output:
        resp.explanation = llm_output.get("explanation")
        resp.uncertainty = llm_output.get("uncertainty")
        resp.suggested_next_step = llm_output.get("suggested_next_step")
    
    return resp

