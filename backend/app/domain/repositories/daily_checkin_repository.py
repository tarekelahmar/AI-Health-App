from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.domain.models.daily_checkin import DailyCheckIn


class DailyCheckInRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_for_date(self, user_id: int, checkin_date: date, **fields) -> DailyCheckIn:
        existing = (
            self.db.query(DailyCheckIn)
            .filter(DailyCheckIn.user_id == user_id, DailyCheckIn.checkin_date == checkin_date)
            .first()
        )
        if existing:
            for k, v in fields.items():
                if v is not None:
                    setattr(existing, k, v)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        obj = DailyCheckIn(user_id=user_id, checkin_date=checkin_date, **fields)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get_by_date(self, user_id: int, checkin_date: date) -> Optional[DailyCheckIn]:
        return (
            self.db.query(DailyCheckIn)
            .filter(DailyCheckIn.user_id == user_id, DailyCheckIn.checkin_date == checkin_date)
            .first()
        )

    def list_range(self, user_id: int, start_date: date, end_date: date, limit: int = 90):
        return (
            self.db.query(DailyCheckIn)
            .filter(DailyCheckIn.user_id == user_id)
            .filter(DailyCheckIn.checkin_date >= start_date, DailyCheckIn.checkin_date <= end_date)
            .order_by(DailyCheckIn.checkin_date.desc())
            .limit(limit)
            .all()
        )

