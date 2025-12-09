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
    # For production, use: postgresql+asyncpg://user:pass@host:5432/db
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
    VECTOR_DB_TYPE: str = "chroma"  # "chroma", "pinecone", "weaviate"
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
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",  # Local dev
        "http://localhost:5173",  # Vite dev server
    ]
    
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
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        """Parse DEBUG from string to bool"""
        if isinstance(v, str):
            return v.lower() == "true"
        return bool(v)
    
    @model_validator(mode="after")
    def set_computed_fields(self):
        """Set computed fields based on other settings"""
        # Set LOG_LEVEL based on DEBUG
        if self.DEBUG:
            self.LOG_LEVEL = "DEBUG"
        # Set ALLOWED_ORIGINS based on DEBUG
        if not self.DEBUG and os.getenv("FRONTEND_URL"):
            self.ALLOWED_ORIGINS = [os.getenv("FRONTEND_URL")]
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
    
    # Only validate OpenAI key if RAG is enabled and in production
    if (settings.ENVIRONMENT == "production" and 
        settings.ENABLE_RAG_ENGINE and 
        not settings.OPENAI_API_KEY):
        errors.append("OPENAI_API_KEY is required for RAG functionality in production")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True


# Create a global settings instance for backward compatibility
settings = get_settings()

# Export commonly used settings as module-level variables for backward compatibility
# This allows existing code using `from app.core.config import DATABASE_URL` to still work
DATABASE_URL = settings.DATABASE_URL
OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_MODEL = settings.OPENAI_MODEL
OPENAI_TEMPERATURE = settings.OPENAI_TEMPERATURE
OPENAI_EMBEDDING_MODEL = settings.OPENAI_EMBEDDING_MODEL
HEALTH_ONTOLOGY_PATH = settings.HEALTH_ONTOLOGY_PATH
KNOWLEDGE_BASE_PATH = settings.KNOWLEDGE_BASE_PATH
CHROMA_DB_PATH = settings.CHROMA_DB_PATH
RAG_CHUNK_SIZE = settings.RAG_CHUNK_SIZE
RAG_CHUNK_OVERLAP = settings.RAG_CHUNK_OVERLAP
RAG_RETRIEVER_K = settings.RAG_RETRIEVER_K
ASSESSMENT_DAYS = settings.ASSESSMENT_DAYS
ASSESSMENT_MAX_RESULTS = settings.ASSESSMENT_MAX_RESULTS
API_TITLE = settings.API_TITLE
API_VERSION = settings.APP_VERSION
CORS_ORIGINS = settings.CORS_ORIGINS
CORS_CREDENTIALS = settings.CORS_CREDENTIALS
CORS_METHODS = settings.CORS_METHODS
CORS_HEADERS = settings.CORS_HEADERS
DB_POOL_SIZE = settings.DB_POOL_SIZE
DB_MAX_OVERFLOW = settings.DB_MAX_OVERFLOW
DB_POOL_PRE_PING = settings.DB_POOL_PRE_PING
