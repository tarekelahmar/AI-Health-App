# Security Fixes - Week 2 Progress

## ✅ Risk #6: Metric Unit Mismatch - FIXED

**Status:** COMPLETE

**Changes Made:**

1. **Expanded MetricSpec** (`backend/app/domain/metric_registry.py`):
   - Added `direction`: whether higher is better/worse
   - Added `aggregation`: how to aggregate multiple values (mean/sum/last/max/min)
   - Added `expected_cadence`: how often values are expected (daily/hourly/weekly)
   - Added `valid_units`: list of acceptable units for validation

2. **Created Unit Conversion Service** (`backend/app/domain/unit_conversion.py`):
   - Unit conversion factors for time, percent, count, score, heart_rate, duration_ms
   - `convert_unit()`: converts values between compatible units
   - `validate_unit_compatibility()`: validates if units can be converted
   - Rejects ambiguous or incompatible conversions

3. **Updated Ingestion Endpoints**:
   - `backend/app/api/v1/health_data.py`: Validates and converts units before storage
   - `backend/app/engine/providers/provider_sync_service.py`: Validates and converts units for provider data
   - `backend/app/providers/whoop/whoop_adapter.py`: Ensures timezone-aware timestamps

4. **Timezone Safety**:
   - All timestamps converted to UTC before storage
   - Timezone-naive timestamps assumed UTC
   - Timezone-aware timestamps converted to UTC
   - Database stores timezone-naive UTC timestamps

**Key Features:**
- Prevents "silent wrongness" from unit mismatches
- Converts compatible units (e.g., hours → minutes for sleep_duration)
- Rejects incompatible units with clear error messages
- Ensures all timestamps are timezone-safe

**Example Conversions:**
- `sleep_duration`: hours → minutes (60x conversion)
- `sleep_efficiency`: ratio/decimal → percent (100x conversion)
- `hrv_rmssd`: seconds → milliseconds (1000x conversion)

## Remaining Fixes

### Risk #7: Evaluation Without Adherence Evidence
**Priority:** Week 3
**Status:** IN PROGRESS

### Risk #8: Attribution False Positives
**Priority:** Week 3
**Status:** PENDING

### Risk #10: In-Process Scheduler
**Priority:** Week 4
**Status:** PENDING

