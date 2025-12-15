from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import Base

class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    key = Column(String, index=True, nullable=False)  # e.g. "magnesium_glycinate"
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)          # supplement/lifestyle/etc
    dosage = Column(String, nullable=True)            # free-text MVP
    schedule = Column(String, nullable=True)          # free-text MVP
    notes = Column(Text, nullable=True)

    # --- Safety metadata persisted (K3) ---
    # Store the evaluated safety decision so protocol/loop can reuse it.
    safety_risk_level = Column(String, nullable=True)      # low/moderate/high
    safety_evidence_grade = Column(String, nullable=True)  # A/B/C/D
    safety_boundary = Column(String, nullable=True)        # informational/lifestyle/experiment
    safety_issues_json = Column(Text, nullable=True)       # JSON string of issues
    safety_notes = Column(Text, nullable=True)             # short notes / disclaimer text

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
