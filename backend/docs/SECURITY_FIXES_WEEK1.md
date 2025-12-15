# Week 1 Security Fixes - Progress

## ✅ Risk #1: PHI Exfiltration via Endpoints - FIXED

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

**Remaining Work:**
- Update Pydantic schemas to make `user_id` optional in payloads (since we override it)
- Add automated tests for cross-user access prevention

## ⏳ Risk #2: WHOOP OAuth State Validation - IN PROGRESS

**Issue:** `/providers/whoop/connect` generates state but callback does not validate it.

**Fix Required:**
- Store state server-side with TTL per user/session
- Verify state on callback
- Prevent CSRF attacks

## ⏳ Risk #3: Provider Tokens in Plaintext - IN PROGRESS

**Issue:** `ProviderToken.access_token` and `refresh_token` are raw Text fields.

**Fix Required:**
- Encrypt tokens at application layer
- Use KMS/Envelope encryption
- Rotate tokens
- Never log tokens

## ⏳ Risk #4: Broken Scheduler Job - IN PROGRESS

**Issue:** `scheduler/jobs.py: job_sync_whoop_data` references non-existent code.

**Fix Required:**
- Delete dead job
- Keep only `job_sync_whoop_for_all_users` → `ProviderSyncService`

