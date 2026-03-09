"""Milestone model — tracks user achievements detected by the milestone engine."""

from datetime import datetime, date

from sqlalchemy import Column, Integer, String, Date, DateTime, JSON, ForeignKey, UniqueConstraint

from app.core.database import Base


class Milestone(Base):
    __tablename__ = "milestones"
    __table_args__ = (
        UniqueConstraint("user_id", "milestone_type", "detected_date",
                         name="uq_milestones_user_type_date"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    milestone_type = Column(String, nullable=False)
    # Types: "score_streak", "recovery", "pattern_confirmed",
    #        "consistency", "domain_improvement"

    detected_date = Column(Date, nullable=False, default=date.today)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)  # "achievement", "progress", "consistency"
    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
