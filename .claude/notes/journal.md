# Journal & Mental Health Track

> Last verified: 2026-03-04

## Architecture

```
User submits check-in (0-10 scales + free-text notes)
    |
    v
LLM factor extraction (Anthropic Claude) -- gated by ENABLE_LLM_TRANSLATION env var
    |                                         Falls back to manual picker when disabled
    v
DailyCheckIn stored (energy, mood, stress, focus, sleep_quality, notes, behaviors_json)
    |
    +---> Checkin Bridge: converts 0-10 subjective -> 1-5 HealthDataPoints
    |         so journal data flows into the standard metric pipeline
    |
    +---> Pattern Engine: deterministic detection of 4 pattern types
    |         Floor, Formula, Crash, Boost
    |         Uses Cohen's d for effect sizes. No LLM involved.
    |
    +---> Wellness Score: composite from objective (wearable) + subjective (journal)
```

## Key Files

### Backend
| File | Purpose |
|------|---------|
| `app/engine/journal_pattern_engine.py` | Deterministic pattern detection (Floor/Formula/Crash/Boost) |
| `app/engine/checkin_bridge.py` | Syncs DailyCheckIn -> HealthDataPoint pipeline |
| `app/engine/wellness_score_service.py` | Wellness score computation logic |
| `app/api/v1/journal.py` | Endpoints: extract-factors, patterns, patterns/compute |
| `app/api/v1/checkins.py` | CRUD for daily check-ins |
| `app/api/v1/wellness_score.py` | Score compute, history, daily lookup |
| `app/llm/factor_extraction.py` | LLM text -> structured behavioral factors |
| `app/domain/models/daily_checkin.py` | DailyCheckIn model |
| `app/engine/memory/pattern_manager.py` | Journal patterns feed into memory system |

### Frontend
| File | Purpose |
|------|---------|
| `src/pages/JournalPage.tsx` | Main page (tabs: Today, Insights, History) |
| `src/components/journal/JournalForm.tsx` | Check-in form |
| `src/components/journal/WellnessScoreRing.tsx` | Score visualization |
| `src/components/journal/WellnessTimeline.tsx` | History timeline |
| `src/components/journal/ScoreBreakdown.tsx` | Factor breakdown |
| `src/components/journal/JournalInsights.tsx` | Pattern display |
| `src/components/journal/PatternCard.tsx` | Individual pattern rendering |
| `src/components/journal/FactorTags.tsx` | Factor tag display |
| `src/types/CheckIn.ts` | TypeScript types |
| `src/types/WellnessScore.ts` | TypeScript types |

### Tests
- `tests/unit/test_journal_pattern_engine.py`
- `tests/unit/test_checkin_bridge.py`
- `tests/unit/test_wellness_score.py`
- `tests/unit/test_factor_extraction.py`

## Shared Dependencies (touch carefully)

- `app/engine/loop_runner.py` -- Consumes HealthDataPoints created by checkin_bridge
- `app/engine/memory/pattern_manager.py` -- Journal patterns feed into this
- `app/engine/governance/` -- All insights must pass governance regardless of source

## Conventions

| Item | Value |
|------|-------|
| DailyCheckIn fields | 0-10 integer |
| HealthDataPoint metric values | 1-5 float (via checkin_bridge) |
| Wellness score | 0-100 composite |

## Pattern Detection Thresholds

```python
MIN_ENTRIES_FOR_PATTERNS = 7
MIN_ENTRIES_FOR_CONFIRM = 10
FLOOR_THRESHOLD = 6
HIGH_SCORE_THRESHOLD = 7
LOW_SCORE_THRESHOLD = 4
MIN_EFFECT_SIZE = 0.5    # Cohen's d
STRONG_EFFECT_SIZE = 0.8
MAX_COMBO_SIZE = 3
```

## Known Behavioral Factors

Factor categories: physical, social, routine, substance, wellness, sleep, supplement.
Full list defined in `app/llm/factor_extraction.py` KNOWN_FACTORS dict.

## Lessons Learned
<!-- After corrections or non-obvious discoveries, add entries here. -->
<!-- Format: - **YYYY-MM-DD**: Lesson. Context: what triggered it. -->
