from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from app.core.database import Base


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    hypothesis_factor = Column(String, nullable=False)  # e.g. magnesium_serum
    intervention_type = Column(String, nullable=False)  # supplement / behaviour
    name = Column(String, nullable=False)               # "Magnesium glycinate"

    dose = Column(String, nullable=True)                # "200"
    unit = Column(String, nullable=True)                 # "mg"
    schedule = Column(String, nullable=True)            # "nightly"

    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)

    confidence_before = Column(Float, nullable=False)   # belief before test

    created_at = Column(DateTime, default=datetime.utcnow)

