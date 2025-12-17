import json
from app.api.schemas.insight import InsightResponse
from app.llm.client import translate_insight
from app.domain.claims import get_evidence_grade, get_claim_policy
from app.engine.governance.claim_policy import validate_language, get_policy
from app.domain.health_domains import HealthDomainKey, domain_for_signal

INSIGHT_TYPE_TO_STATUS = {
    "change": "detected",
    "experiment": "evaluated",
    "safety": "detected",  # Safety insights are also "detected" status
}


def transform_insight(domain_insight) -> InsightResponse:
    """
    Converts Insight SQLAlchemy model → API response schema
    
    AUDIT FIX: Robust to malformed metadata JSON - degrades gracefully.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # AUDIT FIX: Parse metadata JSON safely with error handling
    metadata = {}
    if domain_insight.metadata_json:
        if isinstance(domain_insight.metadata_json, dict):
            metadata = domain_insight.metadata_json
        else:
            try:
                metadata = json.loads(domain_insight.metadata_json)
            except (json.JSONDecodeError, TypeError) as e:
                # AUDIT FIX: Degrade gracefully instead of crashing
                logger.warning(
                    "insight_metadata_json_parse_failed",
                    extra={
                        "insight_id": domain_insight.id,
                        "error": str(e),
                        "metadata_json_preview": str(domain_insight.metadata_json)[:200],
                    }
                )
                # Mark as invalid but continue with empty metadata
                metadata = {
                    "_metadata_invalid": True,
                    "_parse_error": str(e),
                }

    metric_key = metadata.get("metric_key", "unknown")

    # Pure metadata: domain assignment is deterministic and membership-based only.
    # Backward compatible: legacy rows may not have domain_key persisted.
    domain_key = None
    raw_domain_key = metadata.get("domain_key")
    if isinstance(raw_domain_key, str) and raw_domain_key:
        try:
            domain_key = HealthDomainKey(raw_domain_key)
        except Exception:
            domain_key = None
    if domain_key is None:
        domain_key = domain_for_signal(metric_key)
    
    # Evidence must be numeric-only per schema: Dict[str, Union[float,int,None]]
    # (No lists/strings). Keep only high-signal numeric fields.
    evidence: dict[str, float | int | None] = {}
    for k in [
        "baseline_mean",
        "recent_mean",
        "baseline_std",
        "z_score",
        "severity_std",
        "days_consistent",
        "slope_per_day",
        "recent_std",
        "instability_ratio",
        "followup_mean",
        "delta",
        "effect_size",
        "window_days",
        "n_points",
        "sample_size",
        "coverage",
        "claim_level",
    ]:
        v = metadata.get(k)
        if isinstance(v, (int, float)) or v is None:
            evidence[k] = v

    # Safety triggers are a list; expose count only.
    triggers = metadata.get("triggers", [])
    if isinstance(triggers, list):
        evidence["triggers_count"] = int(len(triggers))
    
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
    
    # Note: evidence grade/strength are strings; do not include in numeric evidence payload.

    # GOVERNANCE (legacy rows): ensure we never return policy-violating text even if DB contains it.
    title = domain_insight.title or ""
    summary = domain_insight.description or ""
    try:
        claim_level = min(5, max(1, int(confidence * 5) + 1))
        ok, violations = validate_language(claim_level, f"{title} {summary}")
        if not ok:
            # Downgrade to safe deterministic phrasing.
            safe_level = max(1, claim_level - 1)
            policy = get_policy(safe_level)
            title = f"{metric_key}: {policy.level_name} signal"
            summary = f"Recent data {policy.must_use_phrases[0] if policy.must_use_phrases else 'shows'} changes in {metric_key}."
            evidence["policy_sanitized"] = 1
            evidence["claim_level"] = int(safe_level)
    except Exception:
        # FAIL-CLOSED: if validation fails, replace with safe generic language.
        title = f"{metric_key}: signal"
        summary = f"Recent data shows changes in {metric_key}."
        evidence["policy_sanitized"] = 1

    resp = InsightResponse(
        id=domain_insight.id,
        created_at=domain_insight.generated_at,
        title=title,
        summary=summary,
        metric_key=metric_key,
        domain_key=domain_key,
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

