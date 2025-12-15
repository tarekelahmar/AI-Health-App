from sqlalchemy import Column, Integer, String, Date, JSON, ForeignKey, Index
from app.core.database import Base

class InsightSummary(Base):
    __tablename__ = "insight_summaries"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
    period = Column(String, nullable=False)  # "daily" | "weekly"
    summary_date = Column(Date, index=True, nullable=False)

    headline = Column(String, nullable=False)
    narrative = Column(String, nullable=False)

    key_metrics = Column(JSON, nullable=False)        # top metrics affected
    drivers = Column(JSON, nullable=False)            # causes / contributors
    interventions = Column(JSON, nullable=False)      # active interventions
    outcomes = Column(JSON, nullable=False)            # observed effects
    confidence = Column(Integer, nullable=False)       # 0–100

    details_json = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_insight_summaries_user_period_date", "user_id", "period", "summary_date"),
    )

