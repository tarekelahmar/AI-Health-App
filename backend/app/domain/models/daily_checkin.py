from datetime import datetime, date

from sqlalchemy import Column, Integer, String, DateTime, Date, Float, JSON, UniqueConstraint

from app.core.database import Base


class DailyCheckIn(Base):
    """
    Daily check-in captures subjective + behavioral context that wearables don't have:
    - sleep_quality (subjective)
    - stress/mood/energy
    - notes
    - supplement/med adherence (optional, lightweight)
    This becomes the user-facing daily loop and powers better evaluation.
    """
    __tablename__ = "daily_checkins"
    __table_args__ = (
        UniqueConstraint("user_id", "checkin_date", name="uq_daily_checkins_user_date"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)

    checkin_date = Column(Date, nullable=False, default=date.today)

    # Subjective signals (0..10)
    sleep_quality = Column(Integer, nullable=True)   # 0-10
    energy = Column(Integer, nullable=True)          # 0-10
    mood = Column(Integer, nullable=True)            # 0-10
    stress = Column(Integer, nullable=True)          # 0-10

    # Free text (optional)
    notes = Column(String, nullable=True)

    # Optional quick logs (flexible)
    # Example: {"took_magnesium": true, "melatonin_mg": 0.5, "alcohol_units": 2}
    behaviors_json = Column(JSON, default=dict)

    # Optional "adherence summary" if user logs on the same day
    adherence_rate = Column(Float, nullable=True)  # 0..1

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

