"""
Domain Check-in — explicit weekly life domain ratings.

Stores the 5 user-facing domain scores (1.0-10.0) that users rate
directly via the WeeklyDomainCard in the chat flow. These explicit
ratings feed into LifeDomainScore via EMA with alpha=0.5 (stronger
signal than the implicit chat-derived 0.3).

Separate from LifeDomainScore which holds the 10-axis EMA-smoothed
daily snapshots.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, UniqueConstraint, Index

from app.core.database import Base


class DomainCheckin(Base):
    """Explicit weekly life domain check-in."""

    __tablename__ = "domain_checkins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("journal_sessions.id"), nullable=True)
    checkin_date = Column(String(10), nullable=False)  # "YYYY-MM-DD"

    # 5 user-facing domain ratings (1.0-10.0, step 0.5)
    career = Column(Float, nullable=False)
    relationship = Column(Float, nullable=False)
    social = Column(Float, nullable=False)
    health = Column(Float, nullable=False)
    finance = Column(Float, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "checkin_date", name="uq_domain_checkin_user_date"),
        Index("ix_domain_checkin_user_date", "user_id", "checkin_date"),
    )

    def get_scores(self) -> dict[str, float]:
        """Return all 5 domain scores as a dict."""
        return {
            "career": self.career,
            "relationship": self.relationship,
            "social": self.social,
            "health": self.health,
            "finance": self.finance,
        }
