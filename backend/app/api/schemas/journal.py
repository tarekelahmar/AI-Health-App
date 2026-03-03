"""Schemas for Journal API endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Factor Extraction ──────────────────────────────────────────────

class JournalTextPayload(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class ExtractedFactor(BaseModel):
    key: str
    value: Any  # bool, int, float, str
    label: str
    category: str
    icon: str = ""
    source: str = "ai"  # "ai" | "manual"


class FactorExtractionResponse(BaseModel):
    factors: List[ExtractedFactor]
    custom_factors: List[ExtractedFactor]
    extraction_method: str  # "llm" | "manual_only"


# ── Journal Patterns ───────────────────────────────────────────────

class JournalPatternResponse(BaseModel):
    id: int
    pattern_name: str
    pattern_type: str  # floor | formula | crash | boost
    input_factors: List[str]
    output_metric: str
    description: str
    icon: str
    data_summary: str
    confidence: float
    status: str  # hypothesis | confirmed
    mean_with: float
    mean_without: float
    effect_size: float
    exceptions: int
    n_observations: int


class PatternComputeResponse(BaseModel):
    patterns_found: int
    patterns_updated: int
    patterns_new: int
    minimum_entries_met: bool
    entries_count: int
    entries_needed: int = 7
