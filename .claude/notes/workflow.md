# Development Workflow & Reference

> Moved from CLAUDE.md. Load this only when needed for review templates or workflow reference.

---

## Files to Know

| File | Purpose |
|------|---------|
| `backend/app/engine/loop_runner.py` | Core insight generation loop |
| `backend/app/engine/governance/claim_policy.py` | Claim level enforcement |
| `backend/app/domain/health_domains.py` | Canonical domain definitions |
| `backend/app/domain/safety/red_flags.py` | Safety alert rules |
| `backend/app/domain/metrics/registry.py` | Metric definitions |
| `backend/tests/e2e/test_golden_path.py` | Primary E2E test |
| `frontend/src/pages/InsightsFeedPage.tsx` | Main user-facing page |

---

## Implementation Philosophy

### Core Principles

1. **Every feature ships with tests** - No exceptions. Unit tests, integration tests, and for user-facing features, E2E tests.
2. **Measure before optimizing** - Establish baselines and success criteria before building.
3. **Governance first, features second** - Any new capability must pass through the existing governance architecture.
4. **Incremental value delivery** - Each phase delivers something useful to users, not just technical infrastructure.
5. **Document decisions** - Why we built something matters as much as what we built.

### Implementation Phases

```
Phase 0: Stabilization (Foundation)        -- COMPLETE
Phase 1: Data Foundation (Current)         -- IN PROGRESS
Phase 2: Statistical Upgrade
Phase 3: Longitudinal Memory
Phase 4: Cross-Domain Intelligence
Phase 5: Predictive Capabilities
Phase 6: Experiment Framework
Phase 7+: Advanced Features
```

See **ROADMAP.md** for detailed phase plans with deliverables and acceptance criteria.

---

## Phase 0: Stabilization (COMPLETE)

- [x] Resolve the guardrails import hack in `loop_runner.py`
- [x] Unify API client (all modules now use `api/client.ts`)
- [x] Add missing database indexes
- [x] Remove unused Zustand dependency
- [x] Golden Path E2E test
- [x] Fix conftest.py for proper test isolation
- [x] Fix SQLite compatibility (JSON vs JSONB)
- [x] Set up frontend testing (vitest + React Testing Library)
- [x] Create governance component tests (55 tests passing)
- [x] Write tests that prove claim policy enforcement
- [x] Write tests that prove safety gates fire correctly
- [x] Write tests that prove suppression works

---

## Working with Cursor + Claude

This project uses a hybrid workflow:
- **Cursor**: Day-to-day implementation, code writing, debugging
- **Claude**: Strategic direction, code reviews, architectural decisions

### When to Consult Claude

1. **Phase transitions**: Before starting a new phase, review the plan
2. **Architectural decisions**: When multiple approaches exist
3. **Code reviews**: After completing a phase's deliverables
4. **Safety/governance changes**: Any modifications to safety gates, claim policies, or consent
5. **Stuck points**: When Cursor implementation isn't working

### Code Review Request Template

```
Phase: [1-6]
Completed: [list of deliverables]
Files changed: [key files]
Design decisions: [choices made]
Tests passing: [yes/no]
Questions: [specific questions]
```

### Key Documents

| Document | Purpose |
|----------|---------|
| `CLAUDE.md` | Project context, constraints, workstream routing |
| `ROADMAP.md` | Detailed implementation plan |
| `.claude/notes/*.md` | Track-specific context files |
| `backend/tests/e2e/` | E2E test examples |
| `frontend/src/test/` | Frontend test setup |
