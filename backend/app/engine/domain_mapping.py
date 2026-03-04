"""
Domain Mapping — 5 user-facing domains → backend LifeDomainScore columns.

Each user-facing domain maps 1:1 to a primary backend column. No cross-domain
bleed from explicit ratings. The implicit chat-based signals (via SLIDER_DOMAIN_MAP
and CONTEXT_TAG_DOMAIN_MAP in life_domain_scorer.py) already handle cross-domain
inference; mixing explicit + inferred would create confusing feedback loops.
"""

from __future__ import annotations

from typing import Dict, List


# ── 5 user-facing domains ────────────────────────────────────────

USER_FACING_DOMAINS: List[Dict] = [
    {
        "key": "career",
        "label": "Career & Work",
        "emoji": "💼",
        "backend_column": "career_work",
        "low": "Struggling",
        "high": "Thriving",
    },
    {
        "key": "relationship",
        "label": "Relationship",
        "emoji": "❤️",
        "backend_column": "relationship",
        "low": "Distant",
        "high": "Connected",
    },
    {
        "key": "social",
        "label": "Family & Social",
        "emoji": "👥",
        "backend_column": "social_friendships",
        "low": "Isolated",
        "high": "Supported",
    },
    {
        "key": "health",
        "label": "Health",
        "emoji": "💪",
        "backend_column": "physical_health",
        "low": "Poor",
        "high": "Strong",
    },
    {
        "key": "finance",
        "label": "Finance",
        "emoji": "💰",
        "backend_column": "finance",
        "low": "Stressed",
        "high": "Secure",
    },
]

# Quick lookup: user key → backend column name
_KEY_TO_COLUMN = {d["key"]: d["backend_column"] for d in USER_FACING_DOMAINS}

# Valid user-facing domain keys
DOMAIN_KEYS = [d["key"] for d in USER_FACING_DOMAINS]


def expand_to_backend_scores(user_scores: Dict[str, float]) -> Dict[str, float]:
    """Convert 5 user-facing domain ratings to backend column names.

    Args:
        user_scores: e.g. {"career": 7.5, "relationship": 6.0, ...}

    Returns:
        e.g. {"career_work": 7.5, "relationship": 6.0, ...}

    Raises:
        ValueError: if an unknown domain key is provided.
    """
    result: Dict[str, float] = {}
    for key, score in user_scores.items():
        if key not in _KEY_TO_COLUMN:
            raise ValueError(f"Unknown domain key: {key}")
        result[_KEY_TO_COLUMN[key]] = score
    return result
