"""Tests for RAG engine service"""
import pytest
from app.engine.rag.retriever import HealthRAGEngine
from app.config.settings import get_settings

settings = get_settings()


@pytest.mark.skip(reason="Requires OpenAI API key and knowledge base")
def test_rag_engine_initialization():
    """Test RAG engine can be initialized"""
    engine = HealthRAGEngine(settings.KNOWLEDGE_BASE_PATH)
    assert engine is not None

