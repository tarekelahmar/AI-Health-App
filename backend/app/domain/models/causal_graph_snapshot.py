from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Text
from app.core.database import Base


class CausalGraphSnapshot(Base):
    __tablename__ = "causal_graph_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    snapshot_json = Column(Text, nullable=False, default="{}")  # full graph payload for UI

