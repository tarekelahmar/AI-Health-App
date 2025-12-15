# Security Fixes - Week 1 Complete

## Summary

Fixed **6 of 10** critical security risks identified in the audit. All Week 1 priorities are complete.

## ✅ Completed Fixes

### Risk #1: PHI Exfiltration via Endpoints - FIXED ✅
**Status:** COMPLETE

**Fixed Endpoints:**
- All PHI endpoints now use `get_request_user_id` dependency
- Removed `public_router` for PHI endpoints (graphs, adherence)
- Payload `user_id` fields are overridden with authenticated `user_id`

**Files Modified:**
- `backend/app/api/v1/evaluations.py`
- `backend/app/api/v1/protocols.py`
- `backend/app/api/v1/interventions.py`
- `backend/app/api/v1/graphs.py`
- `backend/app/api/v1/adherence.py`
- `backend/app/api/v1/summaries.py`
- `backend/app/api/v1/baselines.py`
- `backend/app/api/v1/outbox.py`

### Risk #2: WHOOP OAuth CSRF Vulnerability - FIXED ✅
**Status:** COMPLETE

**Changes:**
- Created `OAuthState` model for server-side state storage
- State tokens stored with 10-minute TTL
- State validation on callback (one-time use)
- Prevents CSRF attacks

**Files Created:**
- `backend/app/domain/models/oauth_state.py`
- `backend/app/domain/repositories/oauth_state_repository.py`

**Files Modified:**
- `backend/app/api/v1/providers_whoop.py`
- `backend/app/core/database.py`

### Risk #3: Provider Tokens in Plaintext - FIXED ✅
**Status:** COMPLETE

**Changes:**
- Created `TokenEncryptionService` using Fernet symmetric encryption
- Tokens encrypted before storing in database
- Tokens decrypted when reading from database
- Tokens redacted from logs (show only first/last 4 chars)
- Encryption key derived from `SECRET_KEY` using PBKDF2

**Files Created:**
- `backend/app/core/encryption.py`

**Files Modified:**
- `backend/app/domain/repositories/provider_token_repository.py`
- `backend/requirements.txt` (added cryptography)

**Note:** For production, consider upgrading to KMS/Envelope encryption.

### Risk #4: Broken Scheduler Job - FIXED ✅
**Status:** COMPLETE

**Changes:**
- Removed broken `job_sync_whoop_data()` function
- Removed from scheduler registration
- Kept only working `job_sync_whoop_for_all_users()`

**Files Modified:**
- `backend/app/scheduler/jobs.py`
- `backend/app/scheduler/scheduler.py`

### Risk #5: Baseline Recomputation Silent Failures - FIXED ✅
**Status:** COMPLETE

**Changes:**
- Created `BaselineError` and `BaselineUnavailable` exception types
- `recompute_baseline()` now raises typed errors instead of silently failing
- Added explicit insufficient data handling
- Updated callers to handle `BaselineUnavailable` exceptions
- Added structured logging for baseline failures

**Files Created:**
- `backend/app/engine/baseline_errors.py`

**Files Modified:**
- `backend/app/engine/baseline_service.py`
- `backend/app/engine/loop_runner.py`
- `backend/app/api/v1/baselines.py`
- `backend/app/api/v1/health_data.py`

### Risk #9: Auth Mode Inconsistency - FIXED ✅
**Status:** COMPLETE

**Changes:**
- `get_auth_mode()` now uses `get_mode_config()` as single source of truth
- Environment mode enforces auth mode:
  - `dev`: can be public or private (from AUTH_MODE env var)
  - `staging`: always private
  - `production`: always private (fails hard if misconfigured)
- Added startup validation to fail hard if production is misconfigured

**Files Modified:**
- `backend/app/api/auth_mode.py`
- `backend/app/config/environment.py`
- `backend/app/main.py`

## ⏳ Remaining Fixes (Week 2-4)

### Risk #6: Metric Unit Mismatch
**Priority:** Week 2
**Status:** PENDING

**Required:**
- Expand MetricSpec to include directionality, aggregation, expected cadence, valid units
- Implement unit conversion + strict validation
- Make timestamps timezone-safe end-to-end

### Risk #7: Evaluation Without Adherence Evidence
**Priority:** Week 3
**Status:** PENDING

**Required:**
- Require adherence evidence for "helpful" evaluations
- Add uncertainty bands
- Label "insufficient/low confidence" prominently

### Risk #8: Attribution False Positives
**Priority:** Week 3
**Status:** PENDING

**Required:**
- Add FDR / shrinkage / stability checks
- Cap claims
- Require human-confirmable evidence

### Risk #10: In-Process Scheduler
**Priority:** Week 4
**Status:** PENDING

**Required:**
- Replace in-process scheduler with worker + locks
- Enforce idempotency keys on all jobs
- Persist job run status

## Testing Recommendations

1. **Test PHI access control:**
   - Verify users cannot access other users' data in private mode
   - Verify `user_id` query params are ignored in private mode

2. **Test OAuth state validation:**
   - Verify invalid state tokens are rejected
   - Verify expired state tokens are rejected
   - Verify state tokens are one-time use

3. **Test token encryption:**
   - Verify tokens are encrypted in database
   - Verify tokens are decrypted when read
   - Verify tokens are redacted in logs

4. **Test baseline errors:**
   - Verify insufficient data raises `BaselineUnavailable`
   - Verify baseline errors are logged
   - Verify API returns appropriate error codes

5. **Test auth mode enforcement:**
   - Verify production fails to start if AUTH_MODE != "private"
   - Verify staging always uses private mode
   - Verify dev can use public or private

## Next Steps

1. Run tests to verify all fixes
2. Continue with Week 2 priorities (unit conversion, timezone safety)
3. Add automated tests for cross-user access prevention
4. Consider upgrading token encryption to KMS for production

