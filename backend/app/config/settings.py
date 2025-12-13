"""
Application Configuration - Single Source of Truth

This is the primary configuration module using Pydantic Settings.
All configuration should be imported from here: `from app.config.settings import get_settings`
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List
from pydantic import field_validator, model_validator
import os


class Settings(BaseSettings):
    """Centralized configuration from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # App
    APP_NAME: str = "Health AI Coach"
    APP_VERSION: str = "1.0.0"
    API_TITLE: str = "Health App API"
    API_DESCRIPTION: str = "A FastAPI-based health application with AI-powered insights"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/health_app"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_PRE_PING: bool = True
    
    # Redis (for caching & sessions)
    REDIS_URL: str = "redis://localhost:6379"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_TEMPERATURE: float = 0.3
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    
    # Vector DB
    VECTOR_DB_TYPE: str = "chroma"
    CHROMA_DB_PATH: str = "./chroma_db"
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX: str = "health-app"
    
    # File Paths
    HEALTH_ONTOLOGY_PATH: str = "app/core/health_ontology.json"
    KNOWLEDGE_BASE_PATH: str = "knowledge_base/protocols.md"
    
    # RAG Configuration
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    RAG_RETRIEVER_K: int = 3
    
    # Assessment Configuration
    ASSESSMENT_DAYS: int = 30
    ASSESSMENT_MAX_RESULTS: int = 5
    
    # Security
    SECRET_KEY: str = "change-me-in-production"  # MUST be changed in production!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]  # Frontend origins
    CORS_CREDENTIALS: bool = False  # Must be False when using specific origins
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    FRONTEND_URL: str = ""
    
    # Supabase (optional)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    
    # Email (for notifications)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    
    # Wearable integrations
    FITBIT_CLIENT_ID: str = ""
    FITBIT_CLIENT_SECRET: str = ""
    OURA_API_KEY: str = ""
    WHOOP_CLIENT_ID: str = ""
    
    # Feature flags
    ENABLE_EMAIL_ALERTS: bool = True
    ENABLE_RAG_ENGINE: bool = True
    ENABLE_WEARABLE_SYNC: bool = True
    ENABLE_RATE_LIMITING: bool = True
    
    # Rate Limiting
    RATE_LIMIT_INSIGHTS: str = "10/minute"  # Insight generation endpoints
    RATE_LIMIT_LLM: str = "5/minute"  # LLM-backed endpoints (protocols, etc.)
    RATE_LIMIT_AUTH: str = "5/minute"  # Authentication endpoints
    RATE_LIMIT_GENERAL: str = "100/hour"  # General API endpoints
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        """Parse DEBUG from string to bool"""
        if isinstance(v, str):
            return v.lower() == "true"
        return bool(v)
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from string to list"""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @field_validator("CORS_METHODS", mode="before")
    @classmethod
    def parse_cors_methods(cls, v):
        """Parse CORS_METHODS from string to list"""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [method.strip() for method in v.split(",") if method.strip()]
        return v
    
    @field_validator("CORS_HEADERS", mode="before")
    @classmethod
    def parse_cors_headers(cls, v):
        """Parse CORS_HEADERS from string to list"""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [header.strip() for header in v.split(",") if header.strip()]
        return v
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse ALLOWED_ORIGINS from string to list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @model_validator(mode="after")
    def set_computed_fields(self):
        """Set computed fields based on other settings and validate security"""
        if self.DEBUG:
            self.LOG_LEVEL = "DEBUG"
        if not self.DEBUG and self.FRONTEND_URL:
            self.ALLOWED_ORIGINS = [self.FRONTEND_URL]
        
        # Validate security settings
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "change-me-in-production":
                raise ValueError(
                    "SECRET_KEY must be changed from default value in production!"
                )
            if len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters long in production"
                )
        
        return self


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings singleton"""
    return Settings()


def validate_config() -> bool:
    """Validate that required configuration values are set"""
    settings = get_settings()
    errors = []
    
    if not settings.DATABASE_URL:
        errors.append("DATABASE_URL is required")
    
    if (settings.ENVIRONMENT == "production" and 
        settings.ENABLE_RAG_ENGINE and 
        not settings.OPENAI_API_KEY):
        errors.append("OPENAI_API_KEY is required for RAG functionality in production")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True
