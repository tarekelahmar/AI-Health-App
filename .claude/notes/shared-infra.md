# Shared Infrastructure Track

> Last verified: 2026-03-04

## Architecture

```
OBSERVE: Fetch latest data per metric per domain
    |
    v
MODEL: Run detectors (change, trend, instability, change-point)
    |    + Compute baselines, confidence, evidence grades
    |
    v
INTERVENE: Safety gates check first (red flags, guardrails)
    |         Then governance: claim policies, insight suppression
    |
    v
EVALUATE: Score confidence, assign claim level (1-5)
    |        Suppress if duplicate/stale/low-confidence
    |
    v
SYNTHESIZE: Generate explanation (deterministic or LLM)
    |          Transform to API response
    |
    v
InsightResponse -> Frontend
```

## Key Files

### Backend - Core Pipeline
| File | Purpose |
|------|---------|
| `app/engine/loop_runner.py` | Orchestrates full OBSERVE->SYNTHESIZE loop |
| `app/engine/insight_factory.py` | Creates insight payloads for each type |
| `app/engine/signal_builder.py` | Fetches/prepares metric data |
| `app/engine/explanation_generator.py` | Deterministic plain-English explanations |
| `app/api/transformers/insight_transformer.py` | Domain model -> API response |

### Backend - Governance
| File | Purpose |
|------|---------|
| `app/engine/governance/claim_policy.py` | Claim level enforcement (5 levels) |
| `app/engine/governance/insight_suppression.py` | Prevents duplicate/stale insights |
| `app/engine/governance/signal_classifier.py` | Signal classification |
| `app/engine/guardrails/safety_guardrails.py` | Safety gate (always runs first) |
| `app/engine/guardrails/insight_filter.py` | Post-detection filtering |
| `app/domain/claims/claim_policy.py` | EvidenceGrade, ClaimPolicy definitions |

### Backend - Data Layer
| File | Purpose |
|------|---------|
| `app/domain/health_domains.py` | 10 canonical domain definitions |
| `app/domain/models/__init__.py` | All SQLAlchemy models |
| `app/api/schemas/audit.py` | Audit schemas |

### Frontend
| File | Purpose |
|------|---------|
| `src/pages/InsightsFeedPage.tsx` | Main insights feed |
| `src/components/InsightFeed.tsx` | Insight list component |
| `src/types/Insight.ts` | Insight TypeScript types |

### Tests
- `tests/e2e/test_golden_path.py` -- Primary E2E test
- `tests/e2e/test_governance.py` -- Governance pipeline tests
- `tests/unit/engine/test_explanation_generator.py`
- `tests/unit/engine/test_insight_quality.py`

## Claim Policy Levels (never bypass)

| Level | Allowed Verbs | Allowed Actions |
|-------|--------------|-----------------|
| 1 | "may suggest", "preliminary observation" | monitor |
| 2 | "appears to", "data suggests" | monitor, flag |
| 3 | "shows a pattern", "consistent with" | monitor, flag, suggest_experiment |
| 4 | "has changed", "demonstrates" | all except protocol |
| 5 | "confirmed pattern" | all actions |

## Evidence Grades

| Grade | Criteria | Language |
|-------|----------|----------|
| A | High confidence + large sample + good coverage + strong effect | "This finding is based on consistent data with high confidence." |
| B | Moderate confidence or moderate sample | "This pattern is based on moderate data." |
| C | Low-moderate confidence or small sample | "This is based on limited data." |
| D | Low everything | "This is a preliminary observation." |

## Key Behaviors

- **Fail closed**: If governance validation fails, the output is dropped or replaced with conservative fallback. This is intentional.
- **Explanation generator only checks forbidden phrases** (must_not_use), not required phrases (must_use). Must_use phrases were designed for insight titles and are too restrictive for natural language explanations.
- **Insight titles use display_name** from METRIC_REGISTRY, never raw metric_key.
- **Explanations are computed at API response time**, not stored in DB. No migration needed to change them.

## Lessons Learned
<!-- After corrections or non-obvious discoveries, add entries here. -->
<!-- Format: - **YYYY-MM-DD**: Lesson. Context: what triggered it. -->
- **2026-03-04**: The governance validate_language() function checks must_use_phrases AND must_not_use_phrases. For generated explanation text, only check must_not_use (forbidden) phrases. Must_use phrases like "improved" or "changed" were designed for short insight titles, not natural language paragraphs. Checking must_use on explanations causes fail-closed fallback for perfectly good text. Context: 11/31 explanation generator tests failed because explanations didn't contain required title phrases.
- **2026-03-04**: The insight_transformer governance sanitizer was replacing good DB titles (like "Sleep baseline established") with ugly fallback text (like "sleep_duration: evaluated signal") because validate_language() required specific phrases. Fix: only check forbidden phrases for title validation; use METRIC_REGISTRY display_name for fallbacks. Context: User reported titles still showing raw metric_key after first round of fixes.
- **2026-03-04**: loop_runner.py generates insight titles using claim_policy.example_language, producing nonsense like "sleep_duration: This protocol improved HRV by 12%". Always use METRIC_REGISTRY[metric_key].display_name for human-readable titles. Context: traced root cause of ugly titles to 5 places in loop_runner.py.
