"""LLM translation layer - optional, gated, non-decision-making"""

from .client import translate_insight
from .contracts import LLMInsightInput, LLMInsightOutput

__all__ = ["translate_insight", "LLMInsightInput", "LLMInsightOutput"]

