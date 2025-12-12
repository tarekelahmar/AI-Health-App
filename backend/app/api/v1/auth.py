"""Authentication endpoints"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.domain.models.user import User
from app.domain.schemas.user import UserResponse
from app.dependencies import get_user_repo
from app.domain.repositories import UserRepository
from app.config.security import (
    verify_password,
    create_access_token,
    get_current_user
)
from app.config.rate_limiting import rate_limit_ip
from app.config.settings import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/login")
@rate_limit_ip(settings.RATE_LIMIT_AUTH if settings.ENABLE_RATE_LIMITING else "1000/minute")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repo: UserRepository = Depends(get_user_repo)
) -> Dict[str, Any]:
    """
    User login endpoint.
    
    Returns JWT access token on successful authentication.
    """
    user = user_repo.get_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Get current authenticated user's profile"""
    return current_user

