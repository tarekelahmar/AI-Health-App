import json
import os
from typing import Optional
from app.llm.contracts import LLMInsightInput, LLMInsightOutput
from app.llm.prompts import INSIGHT_TRANSLATION_PROMPT

ENABLE_LLM = os.getenv("ENABLE_LLM_TRANSLATION", "false").lower() == "true"

_client: Optional[object] = None

if ENABLE_LLM:
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            _client = OpenAI(api_key=api_key)
        else:
            print("Warning: ENABLE_LLM_TRANSLATION is true but OPENAI_API_KEY is not set")
    except ImportError:
        print("Warning: openai package not installed. LLM translation disabled.")


def translate_insight(insight: LLMInsightInput) -> Optional[LLMInsightOutput]:
    """Translate structured insight to human-readable explanation. Returns None if LLM is disabled or fails."""
    if not ENABLE_LLM or _client is None:
        return None

    try:
        prompt = INSIGHT_TRANSLATION_PROMPT.format(
            insight_json=json.dumps(insight, indent=2)
        )

        response = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        content = response.choices[0].message.content
        if content:
            return json.loads(content)
    except Exception as e:
        # Log error but don't fail - system works without LLM
        print(f"LLM translation failed: {e}")
    
    return None

