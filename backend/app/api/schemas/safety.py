from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SafetyIssueOut(BaseModel):
    code: str
    severity: Literal["low", "moderate", "high"]
    message: str
    details: Optional[Dict[str, Any]] = None


class SafetyDecisionOut(BaseModel):
    allowed: bool
    risk: Literal["low", "moderate", "high"]
    boundary: Literal["informational", "lifestyle", "experiment"]
    evidence_grade: Literal["A", "B", "C", "D"]
    issues: List[SafetyIssueOut] = Field(default_factory=list)


class SafetyEvaluateRequest(BaseModel):
    intervention_key: str
    user_flags: Optional[Dict[str, Any]] = None
    requested_boundary: Optional[str] = None
    requested_evidence: Optional[str] = None

