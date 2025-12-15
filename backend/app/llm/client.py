import json
import os
from typing import Optional
from app.llm.contracts import LLMInsightInput, LLMInsightOutput
from app.llm.prompts import INSIGHT_TRANSLATION_PROMPT
from app.domain.claims import EvidenceGrade, ClaimPolicy

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


def translate_insight(
    insight: LLMInsightInput,
    evidence_grade: Optional[EvidenceGrade] = None,
    claim_policy: Optional[ClaimPolicy] = None,
) -> Optional[LLMInsightOutput]:
    """
    Translate structured insight to human-readable explanation.
    X3: Enforces claim policy based on evidence grade.
    Returns None if LLM is disabled or fails.
    """
    if not ENABLE_LLM or _client is None:
        return None

    # Default to grade D if not provided
    if evidence_grade is None:
        from app.domain.claims import get_evidence_grade
        evidence_grade = get_evidence_grade(
            confidence=insight.get("confidence", 0.0),
            sample_size=insight.get("evidence", {}).get("n_points", 0) or 0,
            coverage=insight.get("evidence", {}).get("coverage", 0.0) or 0.0,
        )
    
    if claim_policy is None:
        from app.domain.claims import get_claim_policy
        claim_policy = get_claim_policy(evidence_grade)

    try:
        prompt = INSIGHT_TRANSLATION_PROMPT.format(
            insight_json=json.dumps(insight, indent=2),
            evidence_grade=evidence_grade.value,
            allowed_verbs=", ".join(claim_policy.allowed_verbs),
            disallowed_verbs=", ".join(claim_policy.disallowed_verbs),
            uncertainty_required="Yes" if claim_policy.uncertainty_required else "No",
            example_phrases="; ".join(claim_policy.example_phrases),
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

