"""
Factor Extraction — LLM-powered text → structured behavioral factors.

Uses Anthropic Claude for translation (text → structured data).
Same gating, safety validation, and fail-closed approach as before.
The LLM's only job is translation; all pattern detection is
done deterministically downstream.

Returns None when LLM is disabled — frontend falls back to manual picker.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


# ── Known Factor Vocabulary ────────────────────────────────────────
# Factor keys the system recognises. These align with driver_registry.py
# so CrossSignalAttributionEngine can consume them from behaviors_json.

KNOWN_FACTORS: Dict[str, Dict[str, str]] = {
    # Physical
    "exercised": {"type": "bool", "label": "Exercised", "category": "physical", "icon": "🏃"},
    "exercise_type": {"type": "string", "label": "Exercise Type", "category": "physical", "icon": "🏋️"},
    "exercise_minutes": {"type": "int", "label": "Exercise Duration (min)", "category": "physical", "icon": "⏱️"},
    # Social
    "social_contact": {"type": "bool", "label": "Social Contact", "category": "social", "icon": "👥"},
    "isolated": {"type": "bool", "label": "Isolated", "category": "social", "icon": "🏠"},
    # Routine / Structure
    "structured_day": {"type": "bool", "label": "Structured Day", "category": "routine", "icon": "📋"},
    "worked": {"type": "bool", "label": "Worked", "category": "routine", "icon": "💼"},
    "work_from_office": {"type": "bool", "label": "Office Day", "category": "routine", "icon": "🏢"},
    # Substances
    "alcohol": {"type": "bool", "label": "Alcohol", "category": "substance", "icon": "🍷"},
    "alcohol_units": {"type": "int", "label": "Alcohol Units", "category": "substance", "icon": "🍺"},
    "caffeine_late": {"type": "bool", "label": "Late Caffeine", "category": "substance", "icon": "☕"},
    # Wellness practices
    "meditation": {"type": "bool", "label": "Meditation", "category": "wellness", "icon": "🧘"},
    "outdoors": {"type": "bool", "label": "Time Outdoors", "category": "wellness", "icon": "🌳"},
    "cold_exposure": {"type": "bool", "label": "Cold Exposure", "category": "wellness", "icon": "🧊"},
    # Sleep-adjacent
    "napped": {"type": "bool", "label": "Napped", "category": "sleep", "icon": "😴"},
    "late_screen": {"type": "bool", "label": "Late Screen Time", "category": "sleep", "icon": "📱"},
    # Supplements
    "magnesium": {"type": "bool", "label": "Magnesium", "category": "supplement", "icon": "💊"},
    "melatonin": {"type": "bool", "label": "Melatonin", "category": "supplement", "icon": "🌙"},
    "omega3": {"type": "bool", "label": "Omega-3", "category": "supplement", "icon": "🐟"},
    "vitamin_d": {"type": "bool", "label": "Vitamin D", "category": "supplement", "icon": "☀️"},
}

FACTOR_KEYS = list(KNOWN_FACTORS.keys())


# ── Response Schemas ───────────────────────────────────────────────

class CustomFactor(BaseModel):
    key: str = Field(..., min_length=1, max_length=50)
    value: Any
    label: str = Field(..., min_length=1, max_length=80)


class FactorExtractionResult(BaseModel):
    factors: Dict[str, Any] = Field(default_factory=dict)
    custom_factors: List[CustomFactor] = Field(default_factory=list)


# ── Prompt ─────────────────────────────────────────────────────────

FACTOR_EXTRACTION_PROMPT = """You are a structured data extractor for a personal wellness journal.
Given a journal entry, extract behavioral factors that are explicitly stated or clearly implied.

Rules:
- ONLY extract what is explicitly stated or clearly implied in the text
- Do NOT infer medical diagnoses or conditions
- Do NOT interpret emotional content beyond what is written
- Return ONLY factors that map to the known vocabulary below
- For clearly stated behaviors not in the vocabulary, use custom_factors
- Keep custom factor keys in snake_case
- Boolean factors: true if the person did it, false ONLY if they explicitly said they didn't
- Only include a factor if it's mentioned — don't include factors that aren't discussed

Known factor keys and their meanings:
{factor_descriptions}

Journal entry:
---
{journal_text}
---

Respond ONLY in valid JSON (no markdown, no explanation):
{{
  "factors": {{
    "factor_key": true_or_false_or_number
  }},
  "custom_factors": [
    {{"key": "snake_case_name", "value": true, "label": "Human Readable Label"}}
  ]
}}

Only include factors that are clearly present in the text. An empty result is fine."""


def _build_factor_descriptions() -> str:
    """Build human-readable factor descriptions for the prompt."""
    lines = []
    for key, meta in KNOWN_FACTORS.items():
        lines.append(f"- {key} ({meta['type']}): {meta['label']}")
    return "\n".join(lines)


# ── Main Function ──────────────────────────────────────────────────

def extract_factors_from_text(journal_text: str) -> Optional[FactorExtractionResult]:
    """
    Extract structured behavioral factors from journal free text.

    Uses Anthropic Claude with the same gating approach as llm/client.py.
    Returns None if LLM is disabled, text is empty, or extraction fails.
    """
    if not journal_text or not journal_text.strip():
        return None

    enable_llm = os.getenv("ENABLE_LLM_TRANSLATION", "false").lower() == "true"
    if not enable_llm:
        logger.info("LLM disabled — factor extraction skipped")
        return None

    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed — factor extraction unavailable")
        return None

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — factor extraction unavailable")
        return None

    prompt = FACTOR_EXTRACTION_PROMPT.format(
        factor_descriptions=_build_factor_descriptions(),
        journal_text=journal_text.strip()[:3000],  # Cap input length
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text if response.content else None
        if not content:
            logger.warning("LLM returned empty response for factor extraction")
            return None

        # Strip markdown fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()

        # Parse JSON
        parsed = json.loads(content)

        # Validate via Pydantic
        result = FactorExtractionResult(**parsed)

        # Filter: only keep factors from known vocabulary
        clean_factors = {}
        for key, value in result.factors.items():
            if key in KNOWN_FACTORS:
                clean_factors[key] = value

        result.factors = clean_factors

        # Filter custom factors: reject medical/diagnostic terms
        blocked_terms = {
            "diagnos", "prescri", "medicat", "disease", "disorder",
            "syndrome", "treatment", "therapy", "symptom",
        }
        clean_custom = []
        for cf in result.custom_factors:
            label_lower = cf.label.lower()
            key_lower = cf.key.lower()
            if not any(term in label_lower or term in key_lower for term in blocked_terms):
                clean_custom.append(cf)
        result.custom_factors = clean_custom[:5]  # Cap at 5 custom factors

        logger.info(
            f"Extracted {len(result.factors)} known factors, "
            f"{len(result.custom_factors)} custom factors"
        )
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Factor extraction: invalid JSON from LLM: {e}")
        return None
    except ValidationError as e:
        logger.error(f"Factor extraction: schema validation failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Factor extraction failed: {e}")
        return None
