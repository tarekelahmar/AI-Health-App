from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Literal

"""
Claim Boundary Rules (NON-NEGOTIABLE)

Each confidence level enforces language + action constraints to prevent overclaiming.
"""


@dataclass(frozen=True)
class ClaimPolicy:
    """Policy for what claims and actions are allowed at each confidence level"""
    level: int
    level_name: str
    allowed_actions: List[str]
    must_use_phrases: List[str]
    must_not_use_phrases: List[str]
    example_language: str


# Claim policies for each confidence level
CLAIM_POLICIES: Dict[int, ClaimPolicy] = {
    1: ClaimPolicy(
        level=1,
        level_name="observational",
        allowed_actions=["monitor"],
        must_use_phrases=["has changed", "shows", "trend"],
        must_not_use_phrases=["causes", "proves", "improves", "worsens", "recommend"],
        example_language="Sleep duration has declined over 10 days",
    ),
    2: ClaimPolicy(
        level=2,
        level_name="correlational",
        allowed_actions=["monitor"],
        must_use_phrases=["associated with", "correlated with", "co-occurs with"],
        must_not_use_phrases=["causes", "proves", "recommend", "prescribe"],
        example_language="Late caffeine is associated with worse sleep",
    ),
    3: ClaimPolicy(
        level=3,
        level_name="attributed",
        allowed_actions=["monitor", "suggest_experiment"],
        must_use_phrases=["appears to", "may", "suggests", "worth testing"],
        must_not_use_phrases=["causes", "proves", "prescribe", "definitely"],
        example_language="On days you take magnesium, sleep appears to improve next day. Worth testing with an experiment.",
    ),
    4: ClaimPolicy(
        level=4,
        level_name="evaluated",
        allowed_actions=["monitor", "suggest_experiment", "continue_protocol"],
        must_use_phrases=["improved", "changed", "effect size", "with adherence"],
        must_not_use_phrases=["cures", "guarantees", "always works"],
        example_language="This protocol improved HRV by 12% with 85% adherence",
    ),
    5: ClaimPolicy(
        level=5,
        level_name="reconfirmed",
        allowed_actions=["monitor", "suggest_experiment", "continue_protocol"],
        must_use_phrases=["consistently", "repeated", "reliable pattern"],
        must_not_use_phrases=["cures", "guarantees", "always works"],
        example_language="This effect has occurred 3 times consistently",
    ),
}


def get_policy(level: int) -> ClaimPolicy:
    """Get claim policy for a confidence level"""
    if level < 1 or level > 5:
        raise ValueError(f"Invalid confidence level: {level}. Must be 1-5.")
    return CLAIM_POLICIES[level]


def is_action_allowed(level: int, action: str) -> bool:
    """Check if an action is allowed at a given confidence level"""
    policy = get_policy(level)
    return action in policy.allowed_actions


def validate_language(level: int, text: str) -> tuple[bool, List[str]]:
    """
    Validate that language conforms to claim policy.
    
    Returns:
        (is_valid, violations)
    """
    policy = get_policy(level)
    violations = []
    
    # Check for forbidden phrases
    text_lower = text.lower()
    for forbidden in policy.must_not_use_phrases:
        if forbidden.lower() in text_lower:
            violations.append(f"Must not use: '{forbidden}'")
    
    # Check for required phrases (at least one should be present for levels 2+)
    if level >= 2:
        has_required = any(phrase.lower() in text_lower for phrase in policy.must_use_phrases)
        if not has_required:
            violations.append(f"Should use one of: {', '.join(policy.must_use_phrases)}")
    
    return len(violations) == 0, violations


def get_allowed_actions(level: int) -> List[str]:
    """Get list of allowed actions for a confidence level"""
    policy = get_policy(level)
    return policy.allowed_actions.copy()

