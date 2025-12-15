"""User management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.domain.schemas.user import UserCreate, UserResponse
from app.domain.models.user import User
from app.core.database import get_db
from app.config.security import hash_password, get_current_user
from app.dependencies import get_user_repo
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

# SECURITY FIX (Week 1): Use make_v1_router to enforce auth
router = make_v1_router(prefix="/api/v1/users", tags=["users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    user_repo = Depends(get_user_repo)
):
    """Create a new user"""
    existing = user_repo.get_by_email(user.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed = hash_password(user.password)
    db_user = user_repo.create(
        name=user.name,
        email=user.email,
        hashed_password=hashed
    )
    return db_user


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Get current authenticated user's profile"""
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    authenticated_user_id: int = Depends(get_request_user_id),
    user_repo = Depends(get_user_repo)
) -> UserResponse:
    """
    Get user by ID.
    
    SECURITY FIX (Week 1): Only allow users to view their own profile.
    """
    # SECURITY FIX: Only allow viewing own profile
    if user_id != authenticated_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other user's profile"
        )
    
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/", response_model=list[UserResponse])
def list_users(
    authenticated_user_id: int = Depends(get_request_user_id),
    limit: int = 100,
    offset: int = 0,
    user_repo = Depends(get_user_repo)
) -> list[UserResponse]:
    """
    List all users.
    
    SECURITY FIX (Week 1): Removed - this endpoint exposes PII/PHI.
    For MVP, users should only access their own profile via /me or /{user_id} with ownership check.
    
    TODO: If admin functionality is needed, add admin role check here.
    """
    # SECURITY FIX: Disable list all users endpoint - too risky for PHI exposure
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="List all users endpoint disabled for security. Use /me or /{user_id} to view your own profile."
    )
