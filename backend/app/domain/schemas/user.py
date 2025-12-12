"""User domain schemas for API requests and responses"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime


class UserCreate(BaseModel):
    """Schema for creating a new user"""
    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password (min 8 characters)")
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        # Add more password strength checks if needed
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "password": "securepassword123"
            }
        }


class UserResponse(BaseModel):
    """Schema for user response (excludes sensitive data)"""
    id: int
    name: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "John Doe",
                "email": "john.doe@example.com",
                "created_at": "2024-01-01T00:00:00"
            }
        }

