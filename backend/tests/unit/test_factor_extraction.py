"""
Tests for the Factor Extraction module.

Tests the extraction function's behavior when LLM is disabled,
schema validation, and factor vocabulary.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from app.llm.factor_extraction import (
    extract_factors_from_text,
    FactorExtractionResult,
    KNOWN_FACTORS,
    FACTOR_KEYS,
    _build_factor_descriptions,
)


class TestFactorExtractionWhenDisabled:
    """Tests for when LLM is disabled (default test environment)."""

    def test_returns_none_when_llm_disabled(self):
        """Should return None when ENABLE_LLM_TRANSLATION is false."""
        result = extract_factors_from_text("Went for a run today")
        assert result is None

    def test_returns_none_for_empty_text(self):
        """Should return None for empty text."""
        result = extract_factors_from_text("")
        assert result is None

    def test_returns_none_for_whitespace_text(self):
        """Should return None for whitespace-only text."""
        result = extract_factors_from_text("   \n  ")
        assert result is None


class TestFactorVocabulary:
    """Tests for the known factor vocabulary."""

    def test_known_factors_has_entries(self):
        assert len(KNOWN_FACTORS) > 10

    def test_all_factors_have_required_fields(self):
        for key, meta in KNOWN_FACTORS.items():
            assert "type" in meta, f"Factor {key} missing 'type'"
            assert "label" in meta, f"Factor {key} missing 'label'"
            assert "category" in meta, f"Factor {key} missing 'category'"
            assert "icon" in meta, f"Factor {key} missing 'icon'"

    def test_factor_keys_match_known_factors(self):
        assert set(FACTOR_KEYS) == set(KNOWN_FACTORS.keys())

    def test_build_factor_descriptions(self):
        desc = _build_factor_descriptions()
        assert "exercised" in desc
        assert "meditation" in desc
        assert "bool" in desc


class TestFactorExtractionResult:
    """Tests for the Pydantic schema."""

    def test_valid_result(self):
        result = FactorExtractionResult(
            factors={"exercised": True, "alcohol": False},
            custom_factors=[],
        )
        assert result.factors["exercised"] is True
        assert result.factors["alcohol"] is False

    def test_empty_result(self):
        result = FactorExtractionResult(factors={}, custom_factors=[])
        assert len(result.factors) == 0
        assert len(result.custom_factors) == 0

    def test_result_with_custom_factors(self):
        from app.llm.factor_extraction import CustomFactor
        result = FactorExtractionResult(
            factors={"exercised": True},
            custom_factors=[
                CustomFactor(key="ate_healthy", value=True, label="Ate Healthy"),
            ],
        )
        assert len(result.custom_factors) == 1
        assert result.custom_factors[0].key == "ate_healthy"


def _make_anthropic_mock(content_text):
    """Helper to build a mock Anthropic response."""
    mock_text_block = MagicMock()
    mock_text_block.text = content_text

    mock_response = MagicMock()
    mock_response.content = [mock_text_block]
    return mock_response


class TestFactorExtractionWithMockedLLM:
    """Tests with mocked Anthropic to verify extraction logic."""

    @patch.dict(os.environ, {
        "ENABLE_LLM_TRANSLATION": "true",
        "ANTHROPIC_API_KEY": "test-key",
    })
    def test_successful_extraction(self):
        """Test that valid LLM response is parsed correctly."""
        mock_response = _make_anthropic_mock(
            '{"factors": {"exercised": true, "social_contact": true}, "custom_factors": []}'
        )

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            result = extract_factors_from_text("Went for a run and met friends")

        assert result is not None
        assert result.factors["exercised"] is True
        assert result.factors["social_contact"] is True

    @patch.dict(os.environ, {
        "ENABLE_LLM_TRANSLATION": "true",
        "ANTHROPIC_API_KEY": "test-key",
    })
    def test_filters_unknown_factors(self):
        """Unknown factor keys should be filtered out."""
        mock_response = _make_anthropic_mock(
            '{"factors": {"exercised": true, "made_up_factor": true}, "custom_factors": []}'
        )

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            result = extract_factors_from_text("Went for a run and did something made up")

        assert result is not None
        assert "exercised" in result.factors
        assert "made_up_factor" not in result.factors

    @patch.dict(os.environ, {
        "ENABLE_LLM_TRANSLATION": "true",
        "ANTHROPIC_API_KEY": "test-key",
    })
    def test_filters_medical_custom_factors(self):
        """Custom factors with medical terms should be filtered."""
        mock_response = _make_anthropic_mock(
            '{"factors": {}, "custom_factors": [{"key": "diagnosis_adhd", "value": true, "label": "Diagnosed with ADHD"}, {"key": "ate_healthy", "value": true, "label": "Ate Healthy Meal"}]}'
        )

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            result = extract_factors_from_text("I was diagnosed with something and ate healthy")

        assert result is not None
        assert len(result.custom_factors) == 1
        assert result.custom_factors[0].key == "ate_healthy"

    @patch.dict(os.environ, {
        "ENABLE_LLM_TRANSLATION": "true",
        "ANTHROPIC_API_KEY": "test-key",
    })
    def test_handles_invalid_json_gracefully(self):
        """Invalid JSON from LLM should return None."""
        mock_response = _make_anthropic_mock("not valid json")

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            result = extract_factors_from_text("Some journal text")

        assert result is None

    @patch.dict(os.environ, {
        "ENABLE_LLM_TRANSLATION": "true",
        "ANTHROPIC_API_KEY": "test-key",
    })
    def test_handles_empty_llm_response(self):
        """Empty LLM response should return None."""
        mock_response = MagicMock()
        mock_response.content = []

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            result = extract_factors_from_text("Some journal text")

        assert result is None

    @patch.dict(os.environ, {
        "ENABLE_LLM_TRANSLATION": "true",
        "ANTHROPIC_API_KEY": "test-key",
    })
    def test_strips_markdown_fences(self):
        """LLM sometimes wraps JSON in markdown code fences."""
        mock_response = _make_anthropic_mock(
            '```json\n{"factors": {"exercised": true}, "custom_factors": []}\n```'
        )

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            result = extract_factors_from_text("Went for a run")

        assert result is not None
        assert result.factors["exercised"] is True

    def test_returns_none_without_api_key(self):
        """Should return None when API key is not set."""
        with patch.dict(os.environ, {"ENABLE_LLM_TRANSLATION": "true"}, clear=False):
            # Remove ANTHROPIC_API_KEY if it exists
            env = os.environ.copy()
            env.pop("ANTHROPIC_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                result = extract_factors_from_text("Went for a run")
                assert result is None
