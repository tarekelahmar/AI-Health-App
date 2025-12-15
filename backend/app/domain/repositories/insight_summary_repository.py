from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from app.domain.models.insight_summary import InsightSummary


class InsightSummaryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, summary: InsightSummary):
        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)
        return summary

    def get_latest(self, user_id: int, period: str) -> Optional[InsightSummary]:
        return (
            self.db.query(InsightSummary)
            .filter_by(user_id=user_id, period=period)
            .order_by(InsightSummary.summary_date.desc())
            .first()
        )

