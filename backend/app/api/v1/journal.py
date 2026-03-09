"""
Journal API endpoints.

- POST /extract-factors — LLM-powered text → structured behavioral factors
- POST /companion/analyze — AI companion: inference + response + factor extraction
- GET /patterns — discovered journal patterns for a user
- POST /patterns/compute — trigger pattern recomputation
"""

import json
import logging
from dataclasses import asdict
from typing import List

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.api.schemas.companion import (
    CompanionAnalyzeRequest,
    CompanionAnalyzeResponse,
    CompanionTextResponse,
    ContextTagsResponse,
    DiscrepancyResponse,
    InferredDimensionsResponse,
)
from app.api.schemas.journal import (
    ExtractedFactor,
    FactorExtractionResponse,
    JournalPatternResponse,
    JournalTextPayload,
    PatternComputeResponse,
)
from app.core.database import get_db
from app.domain.models.daily_checkin import DailyCheckIn
from app.llm.factor_extraction import KNOWN_FACTORS, extract_factors_from_text

logger = logging.getLogger(__name__)

router = make_v1_router(prefix="/api/v1/journal", tags=["journal"])


# ── Factor Extraction ──────────────────────────────────────────────


@router.post("/extract-factors", response_model=FactorExtractionResponse)
def extract_factors(
    payload: JournalTextPayload,
    user_id: int = Depends(get_request_user_id),
):
    """
    Extract structured behavioral factors from journal text via LLM.

    Returns extracted factors for user confirmation. If LLM is disabled,
    returns an empty result with extraction_method='manual_only' so the
    frontend can show a manual factor picker instead.
    """
    result = extract_factors_from_text(payload.text)

    if result is None:
        # LLM disabled or failed — return empty for manual entry
        return FactorExtractionResponse(
            factors=[],
            custom_factors=[],
            extraction_method="manual_only",
        )

    # Convert dict factors to ExtractedFactor list
    factor_list = []
    for key, value in result.factors.items():
        meta = KNOWN_FACTORS.get(key, {})
        factor_list.append(ExtractedFactor(
            key=key,
            value=value,
            label=meta.get("label", key),
            category=meta.get("category", "other"),
            icon=meta.get("icon", ""),
            source="ai",
        ))

    # Convert custom factors
    custom_list = []
    for cf in result.custom_factors:
        custom_list.append(ExtractedFactor(
            key=cf.key,
            value=cf.value,
            label=cf.label,
            category="custom",
            icon="🏷️",
            source="ai",
        ))

    return FactorExtractionResponse(
        factors=factor_list,
        custom_factors=custom_list,
        extraction_method="llm",
    )


# ── Journal Patterns ───────────────────────────────────────────────


@router.get("/patterns", response_model=List[JournalPatternResponse])
def get_journal_patterns(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Get discovered journal patterns for a user."""
    from app.engine.memory.pattern_manager import PatternManager

    mgr = PatternManager(db)
    patterns = mgr.get_active_patterns(user_id=user_id)

    # Filter to journal-sourced patterns (those with pattern_name in relationship)
    results = []
    for p in patterns:
        rel = p.relationship_json or {}
        if not rel.get("pattern_name"):
            continue
        results.append(JournalPatternResponse(
            id=p.id,
            pattern_name=rel.get("pattern_name", ""),
            pattern_type=p.pattern_type,
            input_factors=p.input_signals_json or [],
            output_metric=p.output_signal or "",
            description=rel.get("description", ""),
            icon=rel.get("icon", "📊"),
            data_summary=rel.get("data_summary", ""),
            confidence=p.current_confidence,
            status=p.status,
            mean_with=rel.get("mean_with", 0),
            mean_without=rel.get("mean_without", 0),
            effect_size=rel.get("effect_size", 0),
            exceptions=rel.get("exceptions", 0),
            n_observations=p.times_observed,
        ))

    # Sort: confirmed first, then by confidence descending
    results.sort(key=lambda r: (0 if r.status == "confirmed" else 1, -r.confidence))
    return results


@router.post("/patterns/compute", response_model=PatternComputeResponse)
def compute_patterns(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Trigger journal pattern recomputation."""
    from app.engine.journal_pattern_engine import compute_journal_patterns

    result = compute_journal_patterns(db=db, user_id=user_id)
    return result


# ── Companion Analysis ────────────────────────────────────────────


@router.post("/companion/analyze", response_model=CompanionAnalyzeResponse)
def companion_analyze(
    payload: CompanionAnalyzeRequest,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """
    Generate AI companion response for a saved check-in entry.

    Combines: factor extraction + dimension inference + context tags +
    companion response text + deterministic discrepancy detection.

    Call this after saving a check-in. The companion analyses the entry
    in context of recent history and known patterns.
    """
    from app.engine.journal_companion import generate_companion_response

    # Load the check-in
    checkin = db.query(DailyCheckIn).filter(
        DailyCheckIn.id == payload.checkin_id,
        DailyCheckIn.user_id == user_id,
    ).first()

    if not checkin:
        raise HTTPException(status_code=404, detail="Check-in not found")

    # Generate companion response
    result = generate_companion_response(
        db=db,
        user_id=user_id,
        checkin=checkin,
        depth_level=payload.depth_level,
    )

    # Persist companion results back to the check-in row
    if result.extraction_method == "llm":
        if result.inferred_dimensions:
            checkin.ai_inferred_json = asdict(result.inferred_dimensions)
        if result.context_tags:
            checkin.context_tags_json = asdict(result.context_tags)
        if result.companion_response and result.companion_response.text:
            checkin.ai_response_text = result.companion_response.text
        if result.discrepancies:
            checkin.discrepancy_json = result.discrepancies.to_json()

        # Merge companion-extracted factors into existing behaviors_json
        if result.factors:
            existing = checkin.behaviors_json or {}
            # Companion factors fill gaps; manual (existing) take precedence
            merged = {**result.factors}
            merged.update(existing)  # Existing overrides companion
            checkin.behaviors_json = merged

        checkin.depth_level = result.depth_level

        db.commit()

        # Update life domain scores based on companion analysis
        try:
            from app.engine.life_domain_scorer import update_life_domain_scores
            update_life_domain_scores(db, user_id, checkin)
        except Exception as e:
            logger.error(f"Life domain scoring failed: {e}")

        # Detect milestones
        try:
            from app.engine.milestone_detector import detect_milestones
            detect_milestones(db, user_id)
        except Exception as e:
            logger.error(f"Milestone detection failed: {e}")

        # Log audit event
        _log_companion_audit(db, user_id, checkin.id, result)

    # Build response
    discrepancy_list = []
    if result.discrepancies and result.discrepancies.flagged:
        for d in result.discrepancies.discrepancies:
            discrepancy_list.append(DiscrepancyResponse(
                rule=d.rule,
                description=d.description,
                severity=d.severity,
            ))

    return CompanionAnalyzeResponse(
        extraction_method=result.extraction_method,
        depth_level=result.depth_level,
        factors=result.factors,
        custom_factors=result.custom_factors,
        ai_inferred=(
            InferredDimensionsResponse(**asdict(result.inferred_dimensions))
            if result.inferred_dimensions else None
        ),
        context_tags=(
            ContextTagsResponse(**asdict(result.context_tags))
            if result.context_tags else None
        ),
        companion_response=(
            CompanionTextResponse(
                text=result.companion_response.text,
                pattern_referenced=result.companion_response.pattern_referenced,
                discrepancy_noted=result.companion_response.discrepancy_noted,
            )
            if result.companion_response else None
        ),
        discrepancies=discrepancy_list,
    )


def _log_companion_audit(db: Session, user_id: int, checkin_id: int, result) -> None:
    """Create an AuditEvent for this companion response."""
    try:
        from app.domain.models.audit_event import AuditEvent

        audit = AuditEvent(
            user_id=user_id,
            entity_type="companion_response",
            entity_id=checkin_id,
            decision_type="created",
            decision_reason=f"Companion response generated (depth={result.depth_level}, method={result.extraction_method})",
            source_metrics=json.dumps(["overall_wellbeing", "energy", "mood", "focus", "connection"]),
            detectors_used=json.dumps(["journal_companion", "discrepancy_detector"]),
            safety_checks_applied=json.dumps([
                {"check": "governance_text_validation", "passed": bool(result.companion_response and result.companion_response.text)},
                {"check": "factor_medical_filter", "passed": True},
            ]),
            metadata_json=json.dumps({
                "extraction_method": result.extraction_method,
                "depth_level": result.depth_level,
                "discrepancies_flagged": result.discrepancies.flagged if result.discrepancies else False,
                "factors_extracted": len(result.factors),
            }),
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log companion audit event: {e}")
