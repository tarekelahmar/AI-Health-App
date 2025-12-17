import json
import os
import logging
from typing import Optional
from app.llm.contracts import LLMInsightInput, LLMInsightOutput
from app.llm.prompts import INSIGHT_TRANSLATION_PROMPT
from app.domain.claims import EvidenceGrade, ClaimPolicy

logger = logging.getLogger(__name__)

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
            # AUDIT FIX: Strict schema validation using Pydantic
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"LLM translation failed: Invalid JSON: {e}")
                return None
            
            # AUDIT FIX: Validate against LLMInsightOutput schema strictly
            try:
                from pydantic import ValidationError
                # Convert TypedDict to Pydantic model for validation
                validated_output = LLMInsightOutput(
                    explanation=parsed.get("explanation", ""),
                    uncertainty=parsed.get("uncertainty", ""),
                    suggested_next_step=parsed.get("suggested_next_step", ""),
                )
            except (ValidationError, TypeError, KeyError) as e:
                logger.error(
                    f"LLM output does not match schema: {e}",
                    extra={
                        "parsed_keys": list(parsed.keys()),
                        "error": str(e),
                    }
                )
                return None
            
            # AUDIT FIX: Validate claim policy and hard-block violations
            from app.domain.claims.claim_policy import validate_claim_language
            explanation = validated_output.get("explanation", "")
            if explanation:
                is_valid, violations = validate_claim_language(explanation, evidence_grade)
                if not is_valid:
                    logger.error(
                        f"LLM output violates claim policy - REJECTED: {violations}",
                        extra={
                            "evidence_grade": evidence_grade.value,
                            "violations": violations,
                            "explanation": explanation[:200],  # First 200 chars for debugging
                        }
                    )
                    # AUDIT FIX: Hard-block - return None instead of sanitized output
                    return None
            
            # GOVERNANCE: Apply claim policy enforcement to suggested_next_step
            suggested = validated_output.get("suggested_next_step", "")
            if suggested:
                # Block any language that suggests medical treatments
                blocked_keywords = [
                    "take", "prescribe", "medication", "drug", "dose", "dosage",
                    "treatment", "therapy", "cure", "diagnose", "diagnosis",
                ]
                suggested_lower = suggested.lower()
                if any(keyword in suggested_lower for keyword in blocked_keywords):
                    logger.error(
                        f"LLM output contains treatment recommendation - REJECTED",
                        extra={
                            "suggested_next_step": suggested[:200],
                        }
                    )
                    return None
                
                # GOVERNANCE: Validate suggested_next_step adheres to claim policy
                is_valid, violations = validate_claim_language(suggested, evidence_grade)
                if not is_valid:
                    logger.warning(
                        f"LLM suggested_next_step violates claim policy: {violations}",
                        extra={
                            "evidence_grade": evidence_grade.value,
                            "violations": violations,
                            "suggested_next_step": suggested[:200],
                        }
                    )
                    # Downgrade or drop the suggested_next_step
                    # For now, we'll drop it to be conservative
                    validated_output["suggested_next_step"] = ""
            
            return validated_output
    except json.JSONDecodeError as e:
        logger.error(f"LLM translation failed: Invalid JSON: {e}")
    except Exception as e:
        # Log error but don't fail - system works without LLM
        logger.error(f"LLM translation failed: {e}")
    
    return None

