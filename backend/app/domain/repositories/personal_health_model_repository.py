from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from app.domain.models.personal_health_model import PersonalHealthModel


class PersonalHealthModelRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, user_id: int) -> PersonalHealthModel:
        """Get existing model or create a new one"""
        model = (
            self.db.query(PersonalHealthModel)
            .filter(PersonalHealthModel.user_id == user_id)
            .one_or_none()
        )
        if model:
            return model

        model = PersonalHealthModel(user_id=user_id)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def get(self, user_id: int) -> Optional[PersonalHealthModel]:
        """Get model for user, return None if not found"""
        return (
            self.db.query(PersonalHealthModel)
            .filter(PersonalHealthModel.user_id == user_id)
            .one_or_none()
        )

    def update(self, model: PersonalHealthModel) -> PersonalHealthModel:
        """Update and persist model"""
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

