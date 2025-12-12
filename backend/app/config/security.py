"""Security utilities for authentication and password hashing"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.domain.models.user import User
from app.core.database import get_db
from app.dependencies import get_user_repo
from app.domain.repositories import UserRepository

logger = logging.getLogger(__name__)
settings = get_settings()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password as string
        
    Raises:
        ValueError: If password is empty or too long
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    # Ensure password is bytes and not too long (bcrypt limit is 72 bytes)
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        logger.warning("Password exceeds 72 bytes, truncating")
        password_bytes = password_bytes[:72]
    
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify password using bcrypt.
    
    Args:
        plain: Plain text password to verify
        hashed: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        plain_bytes = plain.encode('utf-8')
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        user_id: User ID to encode in token
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    to_encode = {"sub": str(user_id), "exp": expire}
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repo)
) -> User:
    """
    Verify JWT and return current user.
    
    Args:
        token: JWT token from request
        user_repo: User repository dependency
        
    Returns:
        Authenticated User object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception
    
    try:
        user = user_repo.get_by_id(int(user_id))
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid user ID in token: {e}")
        raise credentials_exception
    
    if user is None:
        raise credentials_exception
    
    return user
