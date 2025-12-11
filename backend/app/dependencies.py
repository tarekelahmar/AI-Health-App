"""Shared dependencies for FastAPI routes"""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.domain.models.user import User


def get_current_user(
    user_id: int,
    db: Session = Depends(get_db)
) -> User:
    """Get current user by ID (placeholder for auth)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def require_user(user_id: int, db: Session = Depends(get_db)) -> User:
    """Require user to exist"""
    return get_current_user(user_id, db)

