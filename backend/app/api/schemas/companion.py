"""Schemas for Journal Companion API endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────

class CompanionAnalyzeRequest(BaseModel):
    """Request to analyse a saved check-in entry."""
    checkin_id: int
    depth_level: int = Field(default=2, ge=1, le=3)


# ── Response submodels ────────────────────────────────────────────

class InferredDimensionsResponse(BaseModel):
    motivation: Optional[float] = None
    anxiety_level: Optional[float] = None
    self_worth: Optional[float] = None
    structure_adherence: Optional[float] = None
    emotional_regulation: Optional[float] = None
    relationship_quality: Optional[float] = None
    sentiment_score: float = 0.0
    inferred_overall: Optional[float] = None


class ContextTagsResponse(BaseModel):
    exercise: Optional[bool] = None
    exercise_type: Optional[str] = None
    social_contact: Optional[str] = None
    work_type: Optional[str] = None
    sleep: Optional[str] = None
    substances: Optional[str] = None
    location: Optional[str] = None
    conflict: Optional[bool] = None
    conflict_with: Optional[str] = None
    achievement: Optional[bool] = None
    achievement_note: Optional[str] = None


class CompanionTextResponse(BaseModel):
    text: str = ""
    pattern_referenced: bool = False
    discrepancy_noted: bool = False


class DiscrepancyResponse(BaseModel):
    rule: str
    description: str
    severity: str


# ── Main response ─────────────────────────────────────────────────

class CompanionAnalyzeResponse(BaseModel):
    """Full companion analysis response."""
    extraction_method: str  # "llm" | "deterministic_only"
    depth_level: int = 2

    # Factor extraction (consolidated)
    factors: Dict[str, Any] = Field(default_factory=dict)
    custom_factors: List[Dict[str, Any]] = Field(default_factory=list)

    # AI-inferred dimensions
    ai_inferred: Optional[InferredDimensionsResponse] = None

    # Context tags
    context_tags: Optional[ContextTagsResponse] = None

    # Companion response text
    companion_response: Optional[CompanionTextResponse] = None

    # Discrepancies (deterministic)
    discrepancies: List[DiscrepancyResponse] = Field(default_factory=list)
