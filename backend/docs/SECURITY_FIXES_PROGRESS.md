# Security Fixes Progress - Week 1

## ✅ Risk #1: PHI Exfiltration via Endpoints - FIXED

**Status:** ✅ COMPLETE

**Fixed Endpoints:**
- ✅ `GET /api/v1/evaluations` - Now uses `get_request_user_id`
- ✅ `POST /api/v1/protocols` - Overrides `payload.user_id` with authenticated `user_id`
- ✅ `GET /api/v1/protocols` - Now uses `get_request_user_id`
- ✅ `POST /api/v1/interventions` - Overrides `payload.user_id` with authenticated `user_id`
- ✅ `GET /api/v1/interventions` - Now uses `get_request_user_id`
- ✅ `GET /api/v1/graphs/*` - Changed from `public_router` to `make_v1_router`, uses `get_request_user_id`
- ✅ `POST /api/v1/graphs/compute` - Now uses `get_request_user_id`
- ✅ `GET /api/v1/graphs/snapshot` - Now uses `get_request_user_id`
- ✅ `POST /api/v1/adherence/log` - Changed from `public_router` to `make_v1_router`, overrides `payload.user_id`
- ✅ `GET /api/v1/summaries/*` - Now uses `get_request_user_id`
- ✅ `POST /api/v1/baselines/recompute` - Overrides `payload.user_id` with authenticated `user_id`
- ✅ `GET /api/v1/outbox` - Now uses `get_request_user_id`

**Changes Made:**
- All PHI endpoints now use `get_request_user_id` dependency
- Removed `public_router` for PHI endpoints (graphs, adherence)
- Payload `user_id` fields are overridden with authenticated `user_id`
- Added security comments explaining the override

## ✅ Risk #2: WHOOP OAuth State Validation - FIXED

**Status:** ✅ COMPLETE

**Changes Made:**
- Created `OAuthState` model to store state tokens server-side
- Created `OAuthStateRepository` with TTL support (10 minutes default)
- Updated `/connect` endpoint to store state in database
- Updated `/callback` endpoint to validate and consume state token
- State tokens are one-time use (deleted after validation)
- Expired tokens are automatically cleaned up

**Files Created:**
- `backend/app/domain/models/oauth_state.py`
- `backend/app/domain/repositories/oauth_state_repository.py`

**Files Modified:**
- `backend/app/api/v1/providers_whoop.py` - Added state validation
- `backend/app/core/database.py` - Registered OAuthState model
- `backend/app/domain/models/__init__.py` - Exported OAuthState
- `backend/app/domain/repositories/__init__.py` - Exported OAuthStateRepository

## ✅ Risk #4: Broken Scheduler Job - FIXED

**Status:** ✅ COMPLETE

**Changes Made:**
- Removed broken `job_sync_whoop_data()` function that referenced non-existent code
- Removed import and registration of broken job from scheduler
- Kept only `job_sync_whoop_for_all_users()` which uses `ProviderSyncService` correctly

**Files Modified:**
- `backend/app/scheduler/jobs.py` - Removed broken job
- `backend/app/scheduler/scheduler.py` - Removed broken job registration

## ⏳ Risk #3: Provider Tokens in Plaintext - IN PROGRESS

**Status:** ⏳ PENDING

**Issue:** `ProviderToken.access_token` and `refresh_token` are raw Text fields.

**Fix Required:**
- Encrypt tokens at application layer
- Use KMS/Envelope encryption
- Rotate tokens
- Never log tokens
- Redact tokens from logs

**Priority:** HIGH - This is a critical security issue for HIPAA compliance.

## Next Steps

1. **Implement token encryption** (Risk #3)
   - Create encryption service
   - Update ProviderToken model to store encrypted tokens
   - Update repository to encrypt/decrypt on save/load
   - Add token redaction to logging

2. **Add automated tests** for cross-user access prevention
   - Test that users cannot access other users' data
   - Test that invalid state tokens are rejected
   - Test that expired state tokens are rejected

3. **Continue with remaining risks** from audit:
   - Risk #5: Baseline recomputation silent failures
   - Risk #6: Metric unit mismatch
   - Risk #7: Evaluation without adherence evidence
   - Risk #8: Attribution false positives
   - Risk #9: Auth mode inconsistency
   - Risk #10: In-process scheduler issues

