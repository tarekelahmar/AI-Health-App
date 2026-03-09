"""Schemas for Life Domain API endpoints."""

from typing import Dict

from pydantic import BaseModel


class LifeDomainScoreResponse(BaseModel):
    score_date: str
    scores: Dict[str, float]  # {domain_key: score}
    total_score: float
