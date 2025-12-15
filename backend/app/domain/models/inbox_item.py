from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Index
from app.core.database import Base

class InboxItem(Base):
    __tablename__ = "inbox_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)

    category = Column(String, nullable=False)  # reminder | insight | experiment | safety | system
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)

    metadata_json = Column(JSON, nullable=True)

    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

Index("ix_inbox_items_user_created", InboxItem.user_id, InboxItem.created_at)

