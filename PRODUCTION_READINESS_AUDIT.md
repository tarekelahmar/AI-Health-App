# PRODUCTION READINESS AUDIT
## Functional Medicine AI Health Platform

**Date:** 2025-01-XX  
**Auditor:** AI Code Review System  
**Scope:** Full codebase audit against intended system design (Steps K → X)  
**Verdict:** **NO-GO** (with remediation path)

---

## A. EXECUTIVE VERDICT

### **NO-GO** ⛔

**This system is NOT safe for onboarding real users with live wearable/lab data.**

### Why NO-GO:

1. **Critical Safety Gaps:** Missing logger import in `loop_runner.py` causes runtime crashes. Consent is not enforced in provider ingestion paths. Evidence grades are computed but not enforced in insight generation.

2. **Architectural Violations:** Insights can be generated synchronously via `/api/v1/insights/run` endpoint, bypassing scheduled job separation. Audit trail model exists but is never populated.

3. **LLM Boundary Risks:** LLM translation is optional but not validated. System can run without LLM, but claim policy validation is not enforced on LLM outputs.

4. **Missing Enforcement:** Claim policies exist but are not enforced during insight creation. Safety guardrails exist but are not consistently applied.

5. **Data Quality:** Unit conversion exists but consent checks are missing in provider sync. Invariants exist but are not called everywhere.

**Estimated Time to GO:** 4-6 weeks of focused remediation.

---

## B. WHAT IS SOLID (DO NOT CHANGE)

✅ **Security Foundation:**
- PHI exfiltration protection via `get_request_user_id`
- OAuth state validation (server-side)
- Token encryption at rest
- Auth mode governance

✅ **Data Quality Infrastructure:**
- Unit conversion service
- Metric registry validation
- Baseline error handling
- Provenance tracking model

✅ **Safety Infrastructure:**
- Red flag detection
- Contraindication checking
- Safety metadata on interventions
- Safety guardrails module

✅ **Attribution Guardrails:**
- FDR correction
- Stability checks
- Minimum sample size requirements
- Confidence adjustment

✅ **Scheduler Idempotency:**
- Job run tracking
- Idempotency keys
- Job wrapper decorator

✅ **LLM Boundaries:**
- LLM is optional (`ENABLE_LLM_TRANSLATION`)
- LLM only translates, never decides
- System works without LLM

✅ **Domain Models:**
- Well-structured models (Insight, Intervention, Evaluation, Narrative, etc.)
- Repository pattern
- Pydantic schemas

---

## C. WHAT IS BROKEN OR UNSAFE (RANKED)

### 🔴 CRITICAL (Blocking Production)

#### C1. Missing Logger Import in `loop_runner.py`
**File:** `backend/app/engine/loop_runner.py:93`  
**Issue:** `logger.warning()` called but `logger` is never imported.  
**Impact:** Runtime crash when baseline retrieval fails.  
**Fix:** Add `import logging; logger = logging.getLogger(__name__)` at top of file.

#### C2. Consent Not Enforced in Provider Ingestion
**Files:** `backend/app/engine/providers/provider_sync_service.py`, `backend/app/api/v1/providers_whoop.py`  
**Issue:** No consent check before syncing WHOOP data.  
**Impact:** Data ingested without user consent, violating Step R.  
**Fix:** Add consent check in `sync_whoop()`:
```python
from app.domain.repositories.consent_repository import ConsentRepository
consent_repo = ConsentRepository(db)
consent = consent_repo.get_latest(user_id)
if not consent or not consent.consents_to_data_analysis:
    raise ValueError("User has not consented to data analysis")
```

#### C3. Insights Can Be Generated Synchronously
**File:** `backend/app/api/v1/insights.py:28-45`  
**Issue:** `POST /api/v1/insights/run` calls `run_loop()` directly, bypassing scheduled jobs.  
**Impact:** Violates Step L requirement: "No insight generation in ingestion paths."  
**Fix:** Remove synchronous endpoint OR make it admin-only with explicit warning.

#### C4. Audit Trail Never Populated
**File:** `backend/app/domain/models/audit_event.py`  
**Issue:** `AuditEvent` model exists but no code creates audit events.  
**Impact:** Step V (Trust Layer) incomplete - no explainability.  
**Fix:** Add audit event creation in:
- `loop_runner.py` (insight creation)
- `intervention_repository.py` (intervention creation)
- `evaluation_service.py` (evaluation creation)
- `narrative_synthesizer.py` (narrative creation)

#### C5. Evidence Grades Not Enforced During Insight Creation
**Files:** `backend/app/engine/loop_runner.py`, `backend/app/engine/detectors/*.py`  
**Issue:** Evidence grades are computed in transformers but not validated during insight creation.  
**Impact:** Insights can be created with invalid evidence grades, violating Step K.  
**Fix:** Add evidence grade validation in `loop_runner.py` before `repo.create()`.

### 🟠 HIGH (Must Fix Before Production)

#### H1. Claim Policy Not Enforced
**File:** `backend/app/engine/governance/claim_policy.py`  
**Issue:** `validate_language()` exists but is never called during insight/narrative creation.  
**Impact:** System can generate insights with forbidden language (e.g., "causes", "proves").  
**Fix:** Call `validate_language()` in:
- `loop_runner.py` (insight creation)
- `narrative_synthesizer.py` (narrative creation)

#### H2. Safety Guardrails Not Consistently Applied
**File:** `backend/app/engine/loop_runner.py:39-65`  
**Issue:** Safety gate runs but only returns early if triggers found. Normal detectors still run.  
**Impact:** Safety alerts may be buried under normal insights.  
**Fix:** Ensure safety gate always runs first and suppresses normal detectors if critical.

#### H3. Loop Decision Not Validated
**File:** `backend/app/engine/loop_orchestrator.py`  
**Issue:** `decide_next_step()` returns actions but no validation that action is allowed per claim policy.  
**Impact:** System may suggest "continue_protocol" for low-confidence evaluations.  
**Fix:** Add action validation using `is_action_allowed()` from claim policy.

#### H4. LLM Output Not Validated
**File:** `backend/app/llm/client.py:66-68`  
**Issue:** LLM output is parsed as JSON but not validated against claim policy.  
**Impact:** LLM may generate forbidden language despite prompt.  
**Fix:** Validate LLM output with `validate_claim_language()` before returning.

#### H5. Invariants Not Called Everywhere
**File:** `backend/app/core/invariants.py`  
**Issue:** Invariant functions exist but are only called in `provider_sync_service.py`.  
**Impact:** Insights, interventions, evaluations can be created without invariant checks.  
**Fix:** Add invariant checks in:
- `InsightRepository.create()`
- `InterventionRepository.create_with_safety()`
- `EvaluationService.evaluate_experiment()`

### 🟡 MEDIUM (Should Fix Soon)

#### M1. Narrative Synthesis Uses Optional LLM Without Validation
**File:** `backend/app/engine/synthesis/narrative_synthesizer.py:225-227`  
**Issue:** LLM translation is optional but output is not validated.  
**Impact:** Invalid language may appear in narratives.  
**Fix:** Validate LLM output before using.

#### M2. Missing "Insufficient Data" First-Class Handling
**File:** `backend/app/engine/loop_runner.py`  
**Issue:** System skips metrics without baselines but doesn't create "insufficient data" insights.  
**Impact:** Users don't know why insights aren't generated.  
**Fix:** Create explicit "insufficient_data" insights when baseline missing.

#### M3. Loop Decision Endpoint Not Protected
**File:** `backend/app/api/v1/loop.py:22`  
**Issue:** No auth check (uses `Depends(get_db)` but not `get_request_user_id`).  
**Impact:** Potential unauthorized loop decisions.  
**Fix:** Add `user_id: int = Depends(get_request_user_id)` and validate ownership.

#### M4. Trust Metadata Not Populated
**File:** `backend/app/domain/models/insight.py`  
**Issue:** `trust_metadata_json` field exists but is never populated.  
**Impact:** Step R incomplete - no trust scoring.  
**Fix:** Populate trust metadata in `loop_runner.py` when creating insights.

#### M5. Missing Explainability Endpoints
**File:** `backend/app/api/v1/`  
**Issue:** No `/api/v1/insights/{id}/explain` or `/api/v1/insights/{id}/evidence` endpoints.  
**Impact:** Step V incomplete - users can't see "why" insights were generated.  
**Fix:** Add explainability endpoints that return audit events + evidence.

---

## D. TOP 10 CONCRETE RISKS (WITH FILE REFERENCES)

### 1. **Runtime Crash: Missing Logger** 🔴
**File:** `backend/app/engine/loop_runner.py:93`  
**Risk:** `NameError: name 'logger' is not defined` when baseline retrieval fails.  
**Impact:** Entire insight generation crashes, no insights for user.  
**Fix:** Add `import logging; logger = logging.getLogger(__name__)`.

### 2. **Consent Bypass in Provider Sync** 🔴
**Files:** `backend/app/engine/providers/provider_sync_service.py:28`, `backend/app/api/v1/providers_whoop.py:95`  
**Risk:** WHOOP data can be synced without user consent.  
**Impact:** Regulatory violation, potential legal issues.  
**Fix:** Add consent check before `sync_whoop()`.

### 3. **Synchronous Insight Generation** 🔴
**File:** `backend/app/api/v1/insights.py:28-45`  
**Risk:** Insights generated on-demand, bypassing scheduled jobs.  
**Impact:** Violates Step L, potential data quality issues, inconsistent timing.  
**Fix:** Remove endpoint OR make admin-only with rate limiting.

### 4. **No Audit Trail Population** 🔴
**File:** `backend/app/domain/models/audit_event.py` (model exists, never used)  
**Risk:** No explainability - can't answer "why did system say this?"  
**Impact:** Regulatory risk, user trust issues.  
**Fix:** Create audit events in all creation paths.

### 5. **Evidence Grades Not Enforced** 🔴
**Files:** `backend/app/engine/loop_runner.py:136-143` (insight creation)  
**Risk:** Insights created without evidence grade validation.  
**Impact:** Invalid insights may be shown to users.  
**Fix:** Validate evidence grade before `repo.create()`.

### 6. **Claim Policy Not Enforced** 🟠
**Files:** `backend/app/engine/loop_runner.py`, `backend/app/engine/synthesis/narrative_synthesizer.py`  
**Risk:** Insights/narratives can use forbidden language ("causes", "proves").  
**Impact:** Overclaiming, potential legal issues.  
**Fix:** Call `validate_language()` before persistence.

### 7. **LLM Output Not Validated** 🟠
**File:** `backend/app/llm/client.py:66-68`  
**Risk:** LLM may generate forbidden language despite prompt.  
**Impact:** Invalid language in user-facing content.  
**Fix:** Validate LLM output with `validate_claim_language()`.

### 8. **Invariants Not Called Everywhere** 🟠
**Files:** `backend/app/domain/repositories/insight_repository.py`, `backend/app/domain/repositories/intervention_repository.py`  
**Risk:** Objects created without invariant checks.  
**Impact:** Data integrity issues, silent failures.  
**Fix:** Add invariant checks in all repository `create()` methods.

### 9. **Loop Decision Not Protected** 🟡
**File:** `backend/app/api/v1/loop.py:22`  
**Risk:** No auth check on loop decision endpoint.  
**Impact:** Unauthorized loop decisions possible.  
**Fix:** Add `get_request_user_id` dependency.

### 10. **Missing Explainability Endpoints** 🟡
**File:** `backend/app/api/v1/insights.py`  
**Risk:** No way to see "why" insights were generated.  
**Impact:** User trust issues, regulatory risk.  
**Fix:** Add `/api/v1/insights/{id}/explain` endpoint.

---

## E. MISSING OR INCOMPLETE STEP MAPPING (K → X)

### ✅ COMPLETE STEPS

- **Step K (Safety & Guardrails):** ✅ Implemented (red flags, contraindications, safety metadata)
- **Step L (Scheduler & Jobs):** ⚠️ Partially complete (jobs exist, but synchronous endpoint bypasses)
- **Step M (Inbox & Notifications):** ✅ Implemented
- **Step N (Notification Dispatch):** ✅ Implemented
- **Step O (Production Readiness):** ✅ Implemented (request IDs, logs, metrics, health)
- **Step P (Insight Synthesis):** ✅ Implemented (deterministic synthesis, optional LLM)
- **Step Q (Auth Governance):** ✅ Implemented
- **Step Q+1 (Provider Adapter):** ⚠️ Partially complete (missing consent check)
- **Step R (Consent & Data Governance):** ⚠️ Partially complete (consent model exists, not enforced)
- **Step S (Mobile-First UX):** ✅ Implemented (frontend components exist)
- **Step T (Attribution & Drivers):** ✅ Implemented (with guardrails)
- **Step U (Decision Governance):** ⚠️ Partially complete (model exists, validation missing)
- **Step V (Trust Layer):** ❌ Incomplete (audit model exists, never populated; no explainability endpoints)
- **Step W1 (Longitudinal Memory):** ✅ Implemented (baselines, personal health model)
- **Step W2 (Confidence & Uncertainty UX):** ⚠️ Partially complete (confidence shown, but "insufficient data" not first-class)
- **Step X (End-to-End Coherence):** ❌ Incomplete (multiple gaps identified above)

### ❌ CRITICAL GAPS

1. **Step L:** Synchronous insight generation endpoint violates "no insight generation in ingestion paths"
2. **Step Q+1:** Consent not checked in provider sync
3. **Step R:** Consent model exists but not enforced
4. **Step U:** Loop decision validation missing
5. **Step V:** Audit trail never populated, no explainability endpoints
6. **Step X:** Multiple safety bypasses, missing enforcement

---

## F. 4-WEEK REMEDIATION PLAN

### WEEK 1: CRITICAL FIXES (Security & Safety)

**Day 1-2: Runtime Fixes**
- [ ] Fix missing logger import in `loop_runner.py`
- [ ] Add consent check in `provider_sync_service.py`
- [ ] Remove or protect synchronous insight endpoint
- [ ] Add auth check to loop decision endpoint

**Day 3-4: Invariant Enforcement**
- [ ] Add invariant checks in `InsightRepository.create()`
- [ ] Add invariant checks in `InterventionRepository.create_with_safety()`
- [ ] Add invariant checks in `EvaluationService.evaluate_experiment()`
- [ ] Test all creation paths fail on invariant violation

**Day 5: Evidence Grade Enforcement**
- [ ] Add evidence grade validation in `loop_runner.py`
- [ ] Ensure all insights have valid evidence grades
- [ ] Test invalid evidence grades are rejected

**Acceptance Criteria:**
- ✅ No runtime crashes
- ✅ Consent enforced in all provider paths
- ✅ All invariants called
- ✅ Evidence grades validated

---

### WEEK 2: SAFETY & CLAIM POLICY ENFORCEMENT

**Day 1-2: Claim Policy Enforcement**
- [ ] Add `validate_language()` calls in `loop_runner.py`
- [ ] Add `validate_language()` calls in `narrative_synthesizer.py`
- [ ] Add LLM output validation in `llm/client.py`
- [ ] Test forbidden language is rejected

**Day 3-4: Safety Guardrails**
- [ ] Ensure safety gate always runs first
- [ ] Suppress normal detectors if critical safety alert
- [ ] Add action validation in `loop_orchestrator.py`
- [ ] Test safety overrides work correctly

**Day 5: Loop Decision Validation**
- [ ] Add action validation using `is_action_allowed()`
- [ ] Ensure low-confidence evaluations can't trigger "continue_protocol"
- [ ] Test all decision paths

**Acceptance Criteria:**
- ✅ Claim policy enforced everywhere
- ✅ Safety guardrails consistent
- ✅ Loop decisions validated
- ✅ No forbidden language in outputs

---

### WEEK 3: TRUST LAYER & EXPLAINABILITY

**Day 1-2: Audit Trail Population**
- [ ] Create audit events in `loop_runner.py` (insight creation)
- [ ] Create audit events in `intervention_repository.py`
- [ ] Create audit events in `evaluation_service.py`
- [ ] Create audit events in `narrative_synthesizer.py`

**Day 3-4: Explainability Endpoints**
- [ ] Add `/api/v1/insights/{id}/explain` endpoint
- [ ] Add `/api/v1/insights/{id}/evidence` endpoint
- [ ] Return audit events + evidence in responses
- [ ] Test endpoints return correct data

**Day 5: Trust Metadata**
- [ ] Populate `trust_metadata_json` in insights
- [ ] Include data quality scores
- [ ] Include coverage, sample size
- [ ] Test trust metadata is complete

**Acceptance Criteria:**
- ✅ All creations have audit events
- ✅ Explainability endpoints work
- ✅ Trust metadata populated
- ✅ Users can see "why" insights were generated

---

### WEEK 4: DATA QUALITY & EDGE CASES

**Day 1-2: Insufficient Data Handling**
- [ ] Create "insufficient_data" insights when baseline missing
- [ ] Make "insufficient data" first-class in UI
- [ ] Test edge cases (no data, partial data)

**Day 3-4: Integration Testing**
- [ ] Test full loop: OBSERVE → MODEL → INTERVENE → EVALUATE → SYNTHESIZE
- [ ] Test safety overrides
- [ ] Test consent enforcement
- [ ] Test claim policy enforcement

**Day 5: Documentation & Final Review**
- [ ] Document all safety mechanisms
- [ ] Document claim policy rules
- [ ] Document consent flow
- [ ] Final code review

**Acceptance Criteria:**
- ✅ Insufficient data handled gracefully
- ✅ Full loop works end-to-end
- ✅ All safety mechanisms tested
- ✅ Documentation complete

---

## G. FINAL RECOMMENDATION

### When is Real-User Testing Acceptable?

**NOT NOW.** System requires 4-6 weeks of remediation before safe for real users.

### Minimum Requirements for GO:

1. ✅ All critical fixes (Week 1) completed
2. ✅ Claim policy enforcement (Week 2) completed
3. ✅ Audit trail populated (Week 3) completed
4. ✅ Integration testing (Week 4) passed
5. ✅ Documentation complete

### Phased Rollout Recommendation:

**Phase 1 (Week 5):** Internal testing with synthetic data
- Test all safety mechanisms
- Verify claim policy enforcement
- Verify audit trail population

**Phase 2 (Week 6):** Beta testing with 5-10 real users
- Monitor for safety issues
- Verify consent flow
- Verify explainability

**Phase 3 (Week 7+):** Gradual rollout
- Start with 50 users
- Monitor closely
- Expand gradually

### Red Flags to Watch:

- ❌ Any runtime crashes
- ❌ Any insights with forbidden language
- ❌ Any data ingested without consent
- ❌ Any missing audit events
- ❌ Any safety bypasses

---

## SUMMARY

**Current State:** NO-GO  
**Estimated Time to GO:** 4-6 weeks  
**Critical Blockers:** 5 (logger, consent, synchronous insights, audit trail, evidence grades)  
**High Priority Issues:** 5 (claim policy, safety guardrails, loop decision, LLM validation, invariants)  
**Medium Priority Issues:** 5 (narrative validation, insufficient data, loop decision auth, trust metadata, explainability)

**The system has a solid foundation but requires focused remediation before production use. The architecture is sound, but enforcement is incomplete.**

---

**END OF AUDIT**

