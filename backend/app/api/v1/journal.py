"""
Journal API endpoints.

- POST /extract-factors — LLM-powered text → structured behavioral factors
- GET /patterns — discovered journal patterns for a user
- POST /patterns/compute — trigger pattern recomputation
"""

from typing import List

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.api.schemas.journal import (
    ExtractedFactor,
    FactorExtractionResponse,
    JournalPatternResponse,
    JournalTextPayload,
    PatternComputeResponse,
)
from app.core.database import get_db
from app.llm.factor_extraction import KNOWN_FACTORS, extract_factors_from_text

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
