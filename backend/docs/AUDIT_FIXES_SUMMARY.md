# Audit Fixes Summary

## All Critical Issues Fixed ✅

### 1. Token Encryption Fail-Open ✅ FIXED
**File**: `backend/app/core/encryption.py`
- **Fix**: Changed `encrypt()` to fail-closed in production/staging
- **Change**: Raises `RuntimeError` if encryption unavailable instead of returning plaintext
- **Validation**: Added startup validation in `main.py` to test encryption before starting

### 2. Job Idempotency Broken ✅ FIXED
**File**: `backend/app/scheduler/job_wrapper.py`
- **Fix**: Changed idempotency key generation to use time buckets instead of date-only
- **Change**: `generate_idempotency_key()` now includes time bucket based on `idempotency_window_seconds`
- **Change**: Added graceful handling of uniqueness constraint violations (concurrent execution)

### 3. APScheduler In-Process ✅ FIXED
**File**: `backend/app/main.py`
- **Fix**: Disabled scheduler in production mode
- **Change**: Scheduler only starts in dev/staging, not production
- **Note**: Production should use dedicated worker process

### 4. Public Metrics Endpoint ✅ FIXED
**File**: `backend/app/api/v1/metrics_system.py`
- **Fix**: Added authentication requirement via `get_request_user_id`
- **Change**: Uses `make_v1_router(public=False)` to enforce auth

### 5. Public System Status ✅ FIXED
**File**: `backend/app/api/v1/system.py`
- **Fix**: Added authentication requirement via `get_request_user_id`
- **Change**: Endpoint now requires auth to prevent security posture leakage

### 6. Public Jobs Endpoint ✅ FIXED
**File**: `backend/app/api/v1/jobs.py`
- **Fix**: Added authentication requirement via `get_request_user_id`
- **Change**: Uses `make_v1_router` to enforce auth

### 7. LLM Output Not Schema-Validated ✅ FIXED
**File**: `backend/app/llm/client.py`
- **Fix**: Added strict Pydantic schema validation for `LLMInsightOutput`
- **Fix**: Hard-block on claim policy violations (returns `None` instead of sanitized output)
- **Fix**: Blocks treatment recommendations in `suggested_next_step`
- **Change**: All violations result in `None` return, preventing unsafe output from reaching users

### 8. Insight Feed Crashes on Malformed JSON ✅ FIXED
**File**: `backend/app/api/transformers/insight_transformer.py`
- **Fix**: Wrapped `json.loads(metadata_json)` in try/except
- **Change**: Degrades gracefully with `_metadata_invalid` marker instead of crashing

### 9. Baseline Zero Default ✅ FIXED
**File**: `backend/app/api/v1/metrics.py`, `backend/app/api/schemas/metrics.py`
- **Fix**: Changed `MetricBaseline` to use `Optional[float]` for `mean` and `std`
- **Fix**: Added `available: bool` and `reason: Optional[str]` fields
- **Change**: Returns `null` baseline with `available=false` instead of misleading `0/0`

### 10. Metric Registry Duplication ✅ FIXED
**Files**: Multiple files updated
- **Fix**: Consolidated all imports to use `app.domain.metric_registry.METRICS`
- **Files Updated**:
  - `backend/app/engine/change_detection.py`
  - `backend/app/services/observe.py`
  - `backend/app/services/data_quality/validate.py`
  - `backend/app/services/data_quality/normalize.py`
  - `backend/app/services/data_quality/__init__.py`
- **Note**: `backend/app/core/metrics.py` still exists but is deprecated. All active code uses `domain.metric_registry`.

### 11. Router Factory Doesn't Enforce Auth ✅ FIXED
**File**: `backend/app/api/router_factory.py`
- **Fix**: Actually enforces auth at router level in private mode
- **Change**: Adds `Depends(get_request_user_id)` to router dependencies when `public=False` and `is_private_mode()`

## Testing Recommendations

1. **Token Encryption**: Test WHOOP connection in production mode - should fail if `SECRET_KEY` not set
2. **Job Idempotency**: Run `dispatch_notifications` job multiple times - should skip gracefully
3. **Auth Endpoints**: Test `/api/v1/metrics`, `/api/v1/system/status`, `/api/v1/jobs` without auth - should return 401
4. **LLM Validation**: Test with invalid JSON or claim violations - should return `None`
5. **Baseline API**: Test with missing baseline - should return `available: false` not `0/0`

## Remaining Work

- **Metric Registry**: Consider deprecating `backend/app/core/metrics.py` entirely after confirming all code uses `domain.metric_registry`
- **Schema Compatibility**: Some code may need updates if `MetricSpec` API differs from `CanonicalMetric` (e.g., `valid_range` vs `min_value/max_value`)

