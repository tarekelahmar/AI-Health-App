from typing import Optional, List
from sqlalchemy.orm import Session
from app.domain.models.user import User


class UserRepository:
    """Data access for User entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.id == user_id)
            .first()
        )

    def get_by_email(self, email: str) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.email == email)
            .first()
        )

    def list_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        return (
            self.db.query(User)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def create(self, *, name: str, email: str, hashed_password: str) -> User:
        user = User(name=name, email=email, hashed_password=hashed_password)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user_id: int) -> None:
        user = self.get_by_id(user_id)
        if not user:
            return
        self.db.delete(user)
        self.db.commit()

