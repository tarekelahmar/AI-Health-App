from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceGrade(str, Enum):
    """
    Evidence grade for WHY we recommend or surface something.
    Keep this simple and strict.
    """
    A = "A"  # strong (e.g., multiple RCTs / guidelines)
    B = "B"  # moderate (e.g., some RCTs / good observational)
    C = "C"  # limited (small studies / mixed)
    D = "D"  # weak (anecdotal / hypothesis / n=1 only)


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class BoundaryCategory(str, Enum):
    """
    What kind of thing is this?
    IMPORTANT: do not allow drift into diagnosis / prescriptions.
    """
    INFORMATIONAL = "informational"  # describe what data shows
    LIFESTYLE = "lifestyle"          # safe, generic options
    EXPERIMENT = "experiment"        # user-run, tracked, reversible, bounded


@dataclass
class SafetyIssue:
    code: str
    severity: RiskLevel
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class SafetyDecision:
    allowed: bool
    risk: RiskLevel
    issues: List[SafetyIssue]
    boundary: BoundaryCategory
    evidence_grade: EvidenceGrade

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "risk": self.risk.value,
            "issues": [
                {"code": i.code, "severity": i.severity.value, "message": i.message, "details": i.details}
                for i in self.issues
            ],
            "boundary": self.boundary.value,
            "evidence_grade": self.evidence_grade.value,
        }

