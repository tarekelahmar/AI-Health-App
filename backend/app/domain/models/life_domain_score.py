"""
Life Domain Scores — 10-axis life satisfaction model.

These 10 life domains are SEPARATE from the 10 health domains
(Sleep, Stress & Nervous System, etc.). Health domains are for
biomarker insights; life domains are for journal-based wellbeing.

Scores are 1.0-10.0 floats, updated via EMA after each journal entry.
Cold start: all domains at 5.0.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, UniqueConstraint, Index, Text
from app.core.database import Base


# The 10 life domains
LIFE_DOMAINS = [
    "career_work",
    "relationship",
    "physical_health",
    "mental_emotional",
    "social_friendships",
    "purpose_meaning",
    "finance",
    "structure_routine",
    "growth_learning",
    "hobbies_play",
]

LIFE_DOMAIN_LABELS = {
    "career_work": "Career & Work",
    "relationship": "Relationship",
    "physical_health": "Physical Health",
    "mental_emotional": "Mental & Emotional",
    "social_friendships": "Social & Friendships",
    "purpose_meaning": "Purpose & Meaning",
    "finance": "Finance",
    "structure_routine": "Structure & Routine",
    "growth_learning": "Growth & Learning",
    "hobbies_play": "Hobbies & Play",
}

DEFAULT_SCORE = 5.0


class LifeDomainScore(Base):
    """Daily snapshot of a user's life domain scores."""
    __tablename__ = "life_domain_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score_date = Column(String(10), nullable=False)  # "YYYY-MM-DD"

    # 10 life domain scores (1.0-10.0)
    career_work = Column(Float, nullable=False, default=DEFAULT_SCORE)
    relationship = Column(Float, nullable=False, default=DEFAULT_SCORE)
    physical_health = Column(Float, nullable=False, default=DEFAULT_SCORE)
    mental_emotional = Column(Float, nullable=False, default=DEFAULT_SCORE)
    social_friendships = Column(Float, nullable=False, default=DEFAULT_SCORE)
    purpose_meaning = Column(Float, nullable=False, default=DEFAULT_SCORE)
    finance = Column(Float, nullable=False, default=DEFAULT_SCORE)
    structure_routine = Column(Float, nullable=False, default=DEFAULT_SCORE)
    growth_learning = Column(Float, nullable=False, default=DEFAULT_SCORE)
    hobbies_play = Column(Float, nullable=False, default=DEFAULT_SCORE)

    # How each domain score was derived
    derivation_json = Column(Text, nullable=True)
    # {domain: {signal_source: "companion_inferred"|"slider_mapped", confidence: 0.7}}

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "score_date", name="uq_life_domain_user_date"),
        Index("ix_life_domain_scores_user_date", "user_id", "score_date"),
    )

    def get_scores(self) -> dict[str, float]:
        """Return all domain scores as a dict."""
        return {d: getattr(self, d) for d in LIFE_DOMAINS}

    def set_score(self, domain: str, value: float) -> None:
        """Set a single domain score, clamped to 1.0-10.0."""
        if domain not in LIFE_DOMAINS:
            raise ValueError(f"Unknown life domain: {domain}")
        setattr(self, domain, max(1.0, min(10.0, value)))

    @property
    def total_score(self) -> float:
        """Sum of all 10 domains (max 100)."""
        return sum(getattr(self, d) for d in LIFE_DOMAINS)
