"""
Application configuration - Backward compatibility layer

This module re-exports settings from app.config to maintain backward compatibility.
All new code should import directly from app.config.
"""

# Import everything from the main config module
from app.config.settings import (
    get_settings,
    Settings,
    validate_config,
    settings,
    # Re-export commonly used settings as module-level variables
    DATABASE_URL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_EMBEDDING_MODEL,
    HEALTH_ONTOLOGY_PATH,
    KNOWLEDGE_BASE_PATH,
    CHROMA_DB_PATH,
    RAG_CHUNK_SIZE,
    RAG_CHUNK_OVERLAP,
    RAG_RETRIEVER_K,
    ASSESSMENT_DAYS,
    ASSESSMENT_MAX_RESULTS,
    API_TITLE,
    API_VERSION,
    CORS_ORIGINS,
    CORS_CREDENTIALS,
    CORS_METHODS,
    CORS_HEADERS,
    DB_POOL_SIZE,
    DB_MAX_OVERFLOW,
    DB_POOL_PRE_PING,
)

# Re-export for backward compatibility
__all__ = [
    "get_settings",
    "Settings",
    "validate_config",
    "settings",
    "DATABASE_URL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_TEMPERATURE",
    "OPENAI_EMBEDDING_MODEL",
    "HEALTH_ONTOLOGY_PATH",
    "KNOWLEDGE_BASE_PATH",
    "CHROMA_DB_PATH",
    "RAG_CHUNK_SIZE",
    "RAG_CHUNK_OVERLAP",
    "RAG_RETRIEVER_K",
    "ASSESSMENT_DAYS",
    "ASSESSMENT_MAX_RESULTS",
    "API_TITLE",
    "API_VERSION",
    "CORS_ORIGINS",
    "CORS_CREDENTIALS",
    "CORS_METHODS",
    "CORS_HEADERS",
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "DB_POOL_PRE_PING",
]
