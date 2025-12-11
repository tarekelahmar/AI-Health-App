"""
Configuration module - re-exports from settings.py for backward compatibility

New code should import directly: `from app.config.settings import get_settings`
Old code can still use: `from app.config import get_settings`
"""
from app.config.settings import (
    get_settings,
    Settings,
    validate_config,
)

# Re-export commonly used settings as module-level variables for backward compatibility
settings = get_settings()
settings_instance = settings
DATABASE_URL = settings_instance.DATABASE_URL
OPENAI_API_KEY = settings_instance.OPENAI_API_KEY
OPENAI_MODEL = settings_instance.OPENAI_MODEL
OPENAI_TEMPERATURE = settings_instance.OPENAI_TEMPERATURE
OPENAI_EMBEDDING_MODEL = settings_instance.OPENAI_EMBEDDING_MODEL
HEALTH_ONTOLOGY_PATH = settings_instance.HEALTH_ONTOLOGY_PATH
KNOWLEDGE_BASE_PATH = settings_instance.KNOWLEDGE_BASE_PATH
CHROMA_DB_PATH = settings_instance.CHROMA_DB_PATH
RAG_CHUNK_SIZE = settings_instance.RAG_CHUNK_SIZE
RAG_CHUNK_OVERLAP = settings_instance.RAG_CHUNK_OVERLAP
RAG_RETRIEVER_K = settings_instance.RAG_RETRIEVER_K
ASSESSMENT_DAYS = settings_instance.ASSESSMENT_DAYS
ASSESSMENT_MAX_RESULTS = settings_instance.ASSESSMENT_MAX_RESULTS
API_TITLE = settings_instance.API_TITLE
API_VERSION = settings_instance.APP_VERSION
CORS_ORIGINS = settings_instance.CORS_ORIGINS
CORS_CREDENTIALS = settings_instance.CORS_CREDENTIALS
CORS_METHODS = settings_instance.CORS_METHODS
CORS_HEADERS = settings_instance.CORS_HEADERS
DB_POOL_SIZE = settings_instance.DB_POOL_SIZE
DB_MAX_OVERFLOW = settings_instance.DB_MAX_OVERFLOW
DB_POOL_PRE_PING = settings_instance.DB_POOL_PRE_PING

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

