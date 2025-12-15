# Testing STEP X — Production Hardening Features

## Quick Start

### 1. Start the Backend Server

```bash
cd backend
make dev
```

Or manually:
```bash
cd backend
source ../venv/bin/activate  # or your virtual environment
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start on **http://localhost:8000**

### 2. Navigate to Swagger UI

Open your browser and go to:
**http://localhost:8000/docs**

This is the interactive API documentation where you can test all endpoints.

## Testing X1-X8 Features

### X1: System-Level Validation & Invariants

**Test in Swagger UI:**

1. **Test Insight Invariants:**
   - Go to `POST /api/v1/insights` (if exists) or create via loop runner
   - Try creating an insight without `metric_key` in metadata → Should fail with validation error

2. **Test Intervention Invariants:**
   - Go to `POST /api/v1/interventions`
   - Try creating an intervention without safety fields → Should fail
   - Create a valid intervention with safety metadata → Should succeed

3. **Test Evaluation Invariants:**
   - Go to `POST /api/v1/evaluations`
   - Try creating evaluation without `baseline_window` or `intervention_window` → Should fail

### X2: Golden Data Sets

**Run Regression Tests:**

```bash
cd backend
pytest tests/integration/test_golden_data_regression.py -v
```

This will:
- Load golden user data
- Run full analytical loop
- Assert reproducibility
- Check safety warnings
- Validate narratives

### X3: Evidence Grading & Claim Boundaries

**Test in Swagger UI:**

1. **Check Evidence Grade in Insights:**
   - Go to `GET /api/v1/insights/feed?user_id=1`
   - Check response - insights should have `evidence.grade` (A, B, C, or D)
   - Check `evidence.strength` (weak, moderate, strong)

2. **Test Claim Policy:**
   - Create an insight with low confidence (< 0.3)
   - Check that LLM translation (if enabled) uses appropriate language
   - Verify uncertainty is mentioned for low-grade evidence

### X4: User-Visible Audit Trail

**Test in Swagger UI:**

1. **List Audit Events:**
   - Go to `GET /api/v1/audit/?user_id=1`
   - Should return list of audit events

2. **Get Audit for Specific Entity:**
   - First, create an insight (via loop runner or API)
   - Then go to `GET /api/v1/audit/entity?entity_type=insight&entity_id={insight_id}&user_id=1`
   - Should show audit trail for that insight including:
     - Source metrics
     - Detectors used
     - Thresholds crossed
     - Safety checks applied

### X5: Failure Modes & Safe Degradation

**Test via API or Code:**

The failure mode functions are integrated into the system. To test:

1. **Insufficient Data:**
   - Create a user with very few data points
   - Run loop → Should detect insufficient data

2. **Baseline Freezing:**
   - Disconnect wearable (stop syncing data)
   - Wait 48+ hours
   - Baselines should be frozen

3. **Low Adherence:**
   - Create evaluation with `adherence_rate < 0.7`
   - Should be marked as unreliable

### X6: Performance & Cost Guardrails

**Test in Swagger UI:**

1. **Check Performance Limits:**
   - Try creating 51 insights in one day → Should be blocked
   - Try creating 4 experiments for same metric → Should be blocked

2. **Check Metrics:**
   - Performance metrics are logged when limits are exceeded
   - Check logs for warnings about runtime or batch size

### X7: Production Mode Switch

**Test in Swagger UI:**

1. **Check System Status:**
   - Go to `GET /api/v1/system/status`
   - Should return:
     ```json
     {
       "env_mode": "dev",
       "auth_mode": "public",
       "providers_enabled": false,
       "safety_status": "relaxed",
       "logging_level": "DEBUG",
       "enable_llm": false
     }
     ```

2. **Test Environment Modes:**
   - Set `ENV_MODE=production` in `.env`
   - Restart server
   - Check `/api/v1/system/status` → Should show `env_mode: "production"`, `auth_mode: "private"`, `safety_status: "strict"`

### X8: Final Exit Criteria

**Use the Checklist:**

See `backend/docs/PRODUCTION_READINESS_CHECKLIST.md` for comprehensive checklist.

**Quick Verification:**

1. **Test Core Functionality:**
   ```bash
   # Run golden data tests
   pytest tests/integration/test_golden_data_regression.py -v
   
   # Check system status
   curl http://localhost:8000/api/v1/system/status
   
   # Check audit trail
   curl "http://localhost:8000/api/v1/audit/?user_id=1"
   ```

2. **Test Invariants:**
   - Try creating invalid objects → Should fail gracefully
   - Check error messages are safe and informative

3. **Test Explainability:**
   - Create an insight
   - Check audit trail shows "why"
   - Check evidence grade shows "how confident"
   - Check degradation states show "what would change"

## Recommended Testing Flow

1. **Start Server:**
   ```bash
   cd backend
   make dev
   ```

2. **Open Swagger UI:**
   - Navigate to: **http://localhost:8000/docs**

3. **Test System Status (X7):**
   - Click on `GET /api/v1/system/status`
   - Click "Try it out"
   - Click "Execute"
   - Verify response shows current environment mode

4. **Test Audit Trail (X4):**
   - Click on `GET /api/v1/audit/`
   - Add query parameter `user_id=1`
   - Click "Execute"
   - Verify audit events are returned

5. **Test Invariants (X1):**
   - Try creating an intervention via `POST /api/v1/interventions`
   - Try without safety fields → Should fail
   - Try with safety fields → Should succeed

6. **Run Golden Data Tests (X2):**
   ```bash
   pytest tests/integration/test_golden_data_regression.py -v
   ```

## Troubleshooting

**Server won't start:**
- Check if port 8000 is already in use
- Check if database is accessible
- Check `.env` file exists and has correct settings

**Endpoints return 401:**
- Check `AUTH_MODE` in `.env` (should be `public` for testing)
- If `private`, you'll need to authenticate first

**No data in responses:**
- Run seed script: `cd backend && python scripts/seed_observables_demo.py`
- Check database has data for user_id=1

