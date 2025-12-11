"""Authentication endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.domain.models.user import User
from app.core.database import get_db
from app.config.security import (
    verify_password, create_access_token, get_current_user
)

router = APIRouter()

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """User login endpoint"""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's profile"""
    return current_user

