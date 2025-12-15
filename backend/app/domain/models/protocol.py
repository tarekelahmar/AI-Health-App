from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import Base

class Protocol(Base):
    __tablename__ = "protocols"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="active")  # active/paused/completed
    version = Column(Integer, nullable=False, default=1)

    interventions_json = Column(Text, nullable=True)  # JSON list (MVP)
    # Aggregated safety summary for the whole protocol (K3)
    safety_summary_json = Column(Text, nullable=True)  # JSON object: {blocked:[], warnings:[], boundary:...}

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
