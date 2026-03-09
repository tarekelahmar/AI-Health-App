# AI Health Platform - Project Context for Claude

> Slim context file loaded every session. Track-specific details live in `.claude/notes/`.

---

## Project Identity

**What this is**: A Functional Medicine AI Health Platform — a personal health operating system that accumulates understanding over years, not an app that gives tips.

**What this is NOT**:
- Not diagnostic (never says "you have X condition")
- Not prescriptive (never says "take X medication")
- Not a replacement for clinical care
- Not engagement-optimized (silent when there's nothing meaningful)

**Core Philosophy**: Safety-first, governance-first, honesty about uncertainty. LLMs translate and narrate; deterministic systems with human-auditable logic make decisions.

---

## Key Constraints (Never Violate)

1. **LLMs never decide** - They translate and narrate only
2. **Fail closed** - If governance fails, drop the output
3. **Claim policies enforced** - Language must match confidence level
4. **Safety gates first** - Red flags checked before normal processing
5. **Consent required** - No analysis without explicit consent
6. **Audit everything** - Every decision logged with explanation

---

## Current Architecture

### Backend (`/backend`)
- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL + SQLAlchemy 2.0 (SQLite for tests)
- **Pattern**: Domain-Driven Design with Repository Pattern

### Key Modules
- `engine/loop_runner.py` - Core OBSERVE -> MODEL -> INTERVENE -> EVALUATE -> SYNTHESIZE loop
- `engine/governance/` - Claim policies, insight suppression
- `engine/guardrails/` - Safety gates, red flags
- `engine/explanation_generator.py` - Deterministic plain-English explanations
- `engine/detectors/` - Change, trend, instability detection
- `engine/attribution/` - Cross-signal attribution with FDR correction
- `domain/health_domains.py` - 10 canonical health domains
- `domain/metrics/registry.py` - Metric definitions with display names and units

### Frontend (`/frontend`)
- **Framework**: React 18.2 + TypeScript (strict)
- **Build**: Vite 5.0
- **Styling**: Tailwind CSS 3.4

### Health Domains (10 Canonical)
1. Sleep
2. Stress & Nervous System
3. Energy & Fatigue
4. Cardiometabolic
5. Gastrointestinal
6. Inflammation & Immune
7. Hormonal & Reproductive
8. Cognitive & Mental Performance
9. Musculoskeletal & Recovery
10. Nutrition & Micronutrients

### Domain Status States
- `NO_DATA` -> `BASELINE_BUILDING` -> `NO_SIGNAL_DETECTED` / `SIGNAL_DETECTED`

---

## Running Tests

```bash
# Backend tests
cd backend
python -m pytest tests/e2e/test_golden_path.py -v -s  # Golden path
python -m pytest tests/ -v --cov=app                   # All with coverage

# Frontend tests
cd frontend
npm test
```

---

## Workstream Context

This project has parallel tracks. At session start, read the context file matching the user's focus.

### Track files (read the relevant one)
- `.claude/notes/journal.md` — Journal, wellness score, check-ins, pattern detection
- `.claude/notes/biomarkers.md` — Wearable providers, detectors, statistics, baselines
- `.claude/notes/shared-infra.md` — Loop runner, governance, guardrails, insight pipeline

### Background (read only when needed)
- `.claude/notes/vision.md` — Full product vision and north-star design
- `.claude/notes/workflow.md` — Dev workflow, code review templates, phase history
- `ROADMAP.md` — Detailed implementation plan with phases and acceptance criteria

### Session protocol
1. User states focus (e.g., "journal track", "biomarkers", "shared infra", "strategic planning")
2. Read the matching `.claude/notes/{track}.md` file
3. Run `git status` and check recent commits
4. For strategic/planning sessions, read `vision.md` and `ROADMAP.md` instead
5. At session end: if a non-obvious lesson was learned, ask user whether to add it to the track's Lessons Learned section

### Lessons Learned workflow
When Claude gets corrected or discovers something non-obvious during a session:
- At a natural pause, say: "I learned that [lesson]. Should I add this to the track notes?"
- If yes, append to the `## Lessons Learned` section of the relevant track file
- Format: `- **YYYY-MM-DD**: Lesson. Context: what triggered it.`

---

*Last updated: March 2026*
*Current phase: Phase 1 (Data Foundation)*
