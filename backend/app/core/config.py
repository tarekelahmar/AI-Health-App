"""Application configuration"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

# ==================== API Configuration ====================
API_TITLE = os.getenv("API_TITLE", "Health App API")
API_VERSION = os.getenv("API_VERSION", "0.1.0")
API_DESCRIPTION = os.getenv("API_DESCRIPTION", "A FastAPI-based health application with AI-powered insights")

# CORS Configuration
CORS_ORIGINS: List[str] = os.getenv(
    "CORS_ORIGINS", 
    "*"
).split(",") if os.getenv("CORS_ORIGINS") != "*" else ["*"]
CORS_CREDENTIALS = os.getenv("CORS_CREDENTIALS", "true").lower() == "true"
CORS_METHODS = os.getenv("CORS_METHODS", "*").split(",")
CORS_HEADERS = os.getenv("CORS_HEADERS", "*").split(",")

# ==================== Database Configuration ====================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/postgres"
)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"

# ==================== File Paths ====================
# Paths relative to backend/ directory
HEALTH_ONTOLOGY_PATH = os.getenv("HEALTH_ONTOLOGY_PATH", "app/core/health_ontology.json")
KNOWLEDGE_BASE_PATH = os.getenv("KNOWLEDGE_BASE_PATH", "knowledge_base/protocols.md")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")

# ==================== OpenAI Configuration ====================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")

# ==================== RAG Configuration ====================
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "500"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))
RAG_RETRIEVER_K = int(os.getenv("RAG_RETRIEVER_K", "3"))

# ==================== Assessment Configuration ====================
ASSESSMENT_DAYS = int(os.getenv("ASSESSMENT_DAYS", "30"))
ASSESSMENT_MAX_RESULTS = int(os.getenv("ASSESSMENT_MAX_RESULTS", "5"))

# ==================== Supabase Configuration (Optional) ====================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# ==================== Environment ====================
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ==================== Validation ====================
def validate_config():
    """Validate that required configuration values are set"""
    errors = []
    
    if not DATABASE_URL:
        errors.append("DATABASE_URL is required")
    
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY is required for RAG functionality")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True

# Validate on import (only in production)
if ENVIRONMENT == "production":
    validate_config()
