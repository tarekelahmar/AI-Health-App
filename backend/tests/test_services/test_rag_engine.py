"""Tests for RAG engine service"""
import pytest
from app.services.rag_engine import HealthRAGEngine
from app.core.config import KNOWLEDGE_BASE_PATH


@pytest.mark.skip(reason="Requires OpenAI API key and knowledge base")
def test_rag_engine_initialization():
    """Test RAG engine can be initialized"""
    engine = HealthRAGEngine(KNOWLEDGE_BASE_PATH)
    assert engine is not None

