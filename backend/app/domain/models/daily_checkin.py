from datetime import datetime, date

from sqlalchemy import Column, Integer, String, DateTime, Date, Float, JSON, UniqueConstraint

from app.core.database import Base


class DailyCheckIn(Base):
    """
    Daily check-in captures subjective + behavioral context that wearables don't have.

    V2 sliders (1.0-10.0 float, step 0.5):
      overall_wellbeing, energy, mood, focus, connection
    V1 sliders (0-10 int, deprecated — kept for backward compat):
      sleep_quality, stress

    AI companion fields (populated by Phase 2 companion service):
      ai_inferred_json, context_tags_json, ai_response_text,
      discrepancy_json, milestone_json
    """
    __tablename__ = "daily_checkins"
    __table_args__ = (
        UniqueConstraint("user_id", "checkin_date", name="uq_daily_checkins_user_date"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)

    checkin_date = Column(Date, nullable=False, default=date.today)

    # ── V2 slider fields (1.0-10.0 float, step 0.5) ─────────────
    overall_wellbeing = Column(Float, nullable=True)  # 1.0-10.0
    energy = Column(Float, nullable=True)             # 1.0-10.0
    mood = Column(Float, nullable=True)               # 1.0-10.0
    focus = Column(Float, nullable=True)              # 1.0-10.0
    connection = Column(Float, nullable=True)         # 1.0-10.0

    # ── V1 slider fields (0-10 int, deprecated — not in V2 form) ─
    sleep_quality = Column(Integer, nullable=True)    # 0-10 (V1 only)
    stress = Column(Integer, nullable=True)           # 0-10 (V1 only)

    # Free text (optional)
    notes = Column(String, nullable=True)

    # Optional quick logs (flexible)
    # Example: {"took_magnesium": true, "melatonin_mg": 0.5, "alcohol_units": 2}
    behaviors_json = Column(JSON, default=dict)

    # Optional "adherence summary" if user logs on the same day
    adherence_rate = Column(Float, nullable=True)  # 0..1

    # ── AI companion fields (Phase 2) ────────────────────────────
    # AI-inferred dimensions: {motivation, anxiety_level, self_worth,
    #   structure_adherence, emotional_regulation, relationship_quality,
    #   sentiment_score, inferred_overall}
    ai_inferred_json = Column(JSON, nullable=True)

    # AI-inferred context tags: {exercise, exercise_type, social_contact,
    #   work_type, sleep, substances, location, conflict, conflict_with,
    #   achievement, achievement_note}
    context_tags_json = Column(JSON, nullable=True)

    # AI companion response text
    ai_response_text = Column(String, nullable=True)

    # Discrepancy detection: {flag: bool, type: str, note: str}
    discrepancy_json = Column(JSON, nullable=True)

    # Milestone detection: {flag: bool, category: str, note: str}
    milestone_json = Column(JSON, nullable=True)

    # ── Entry metadata ───────────────────────────────────────────
    word_count = Column(Integer, nullable=True)
    depth_level = Column(Integer, nullable=True)  # 1, 2, or 3

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_v2(self) -> bool:
        """True if this entry was created with the V2 form (has overall_wellbeing)."""
        return self.overall_wellbeing is not None

