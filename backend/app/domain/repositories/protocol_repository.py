from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.domain.models.protocol import Protocol


class ProtocolRepository:
    """Data access for weekly Protocols."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        week_number: int,
        start_date: datetime,
        end_date: datetime,
        interventions: dict,
        status: str = "active",
    ) -> Protocol:
        protocol = Protocol(
            user_id=user_id,
            week_number=week_number,
            start_date=start_date,
            end_date=end_date,
            interventions=interventions,
            status=status,
        )
        self.db.add(protocol)
        self.db.commit()
        self.db.refresh(protocol)
        return protocol

    def get_by_id(self, protocol_id: int) -> Optional[Protocol]:
        return (
            self.db.query(Protocol)
            .filter(Protocol.id == protocol_id)
            .first()
        )

    def get_active_for_user(self, user_id: int) -> Optional[Protocol]:
        return (
            self.db.query(Protocol)
            .filter(
                Protocol.user_id == user_id,
                Protocol.status == "active",
            )
            .order_by(Protocol.created_at.desc())
            .first()
        )

    def list_history_for_user(
        self,
        user_id: int,
        limit: int = 20,
    ) -> List[Protocol]:
        return (
            self.db.query(Protocol)
            .filter(Protocol.user_id == user_id)
            .order_by(Protocol.start_date.desc())
            .limit(limit)
            .all()
        )

    def update_status(
        self,
        protocol_id: int,
        status: str,
    ) -> Optional[Protocol]:
        protocol = self.get_by_id(protocol_id)
        if not protocol:
            return None
        protocol.status = status
        self.db.commit()
        self.db.refresh(protocol)
        return protocol

