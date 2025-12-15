from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime

"""
User-Facing Confidence Explanation

Exposes *why* confidence is what it is:
- Data coverage
- Adherence rate
- Effect size
- Consistency across time
- Confounder risk
"""


@dataclass
class ConfidenceExplanation:
    """Explanation of why confidence is at a given level"""
    overall_confidence: float
    data_coverage: float  # [0-1] - % of expected data points present
    adherence_rate: Optional[float] = None  # [0-1] - if applicable
    effect_size: Optional[float] = None  # Standardized effect size
    consistency: Optional[float] = None  # [0-1] - consistency across time windows
    confounder_risk: Optional[float] = None  # [0-1] - risk of confounding factors
    sample_size: Optional[int] = None
    days_of_data: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        return {
            "overall_confidence": self.overall_confidence,
            "data_coverage": self.data_coverage,
            "adherence_rate": self.adherence_rate,
            "effect_size": self.effect_size,
            "consistency": self.consistency,
            "confounder_risk": self.confounder_risk,
            "sample_size": self.sample_size,
            "days_of_data": self.days_of_data,
        }
    
    def to_human_readable(self) -> str:
        """Generate human-readable explanation"""
        parts = []
        
        if self.data_coverage < 0.5:
            parts.append("Limited data coverage")
        elif self.data_coverage < 0.8:
            parts.append("Moderate data coverage")
        else:
            parts.append("Good data coverage")
        
        if self.sample_size:
            parts.append(f"based on {self.sample_size} observations")
        
        if self.days_of_data:
            parts.append(f"over {self.days_of_data} days")
        
        if self.adherence_rate is not None:
            if self.adherence_rate < 0.7:
                parts.append("with low adherence")
            elif self.adherence_rate < 0.9:
                parts.append("with moderate adherence")
            else:
                parts.append("with high adherence")
        
        if self.consistency is not None:
            if self.consistency < 0.6:
                parts.append("(inconsistent pattern)")
            elif self.consistency < 0.8:
                parts.append("(moderately consistent)")
            else:
                parts.append("(highly consistent)")
        
        if self.confounder_risk is not None and self.confounder_risk > 0.5:
            parts.append("(possible confounders present)")
        
        return ". ".join(parts) + "."


class ConfidenceExplanationService:
    """Service to generate confidence explanations"""
    
    @staticmethod
    def explain_insight(
        confidence: float,
        data_coverage: float,
        sample_size: Optional[int] = None,
        days_of_data: Optional[int] = None,
        consistency: Optional[float] = None,
    ) -> ConfidenceExplanation:
        """Generate explanation for an insight"""
        return ConfidenceExplanation(
            overall_confidence=confidence,
            data_coverage=data_coverage,
            sample_size=sample_size,
            days_of_data=days_of_data,
            consistency=consistency,
        )
    
    @staticmethod
    def explain_driver(
        confidence: float,
        data_coverage: float,
        effect_size: float,
        sample_size: int,
        days_of_data: int,
        consistency: Optional[float] = None,
        confounder_risk: Optional[float] = None,
    ) -> ConfidenceExplanation:
        """Generate explanation for a driver attribution"""
        return ConfidenceExplanation(
            overall_confidence=confidence,
            data_coverage=data_coverage,
            effect_size=effect_size,
            sample_size=sample_size,
            days_of_data=days_of_data,
            consistency=consistency,
            confounder_risk=confounder_risk,
        )
    
    @staticmethod
    def explain_evaluation(
        confidence: float,
        data_coverage: float,
        adherence_rate: float,
        effect_size: float,
        sample_size: int,
        days_of_data: int,
        consistency: Optional[float] = None,
    ) -> ConfidenceExplanation:
        """Generate explanation for an experiment evaluation"""
        return ConfidenceExplanation(
            overall_confidence=confidence,
            data_coverage=data_coverage,
            adherence_rate=adherence_rate,
            effect_size=effect_size,
            sample_size=sample_size,
            days_of_data=days_of_data,
            consistency=consistency,
        )

