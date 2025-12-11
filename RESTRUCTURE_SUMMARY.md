# Backend & Frontend Restructure - Summary

## ✅ Completed - Backend Structure

### 1. New Directory Structure Created
```
backend/app/
  ├── api/v1/          ✅ All API endpoints moved here
  ├── config/           ✅ settings.py, security.py, logging.py
  ├── domain/
  │   ├── models/      ✅ All SQLAlchemy models
  │   └── schemas/     ✅ All Pydantic schemas
  ├── engine/
  │   ├── analytics/   ✅ time_series, correlation, rolling_metrics
  │   ├── reasoning/   ✅ dysfunction_detector, protocol_generator
  │   ├── rag/         ✅ retriever.py (moved from rag_engine)
  │   └── prompts/     ✅ insight_prompt.txt, protocol_prompt.txt
  ├── core/            ✅ database.py, health_ontology.json
  └── services/        ✅ (existing services remain)
```

### 2. API Endpoints Restructured
- ✅ `api/v1/users.py` - Updated imports
- ✅ `api/v1/auth.py` - New authentication endpoints
- ✅ `api/v1/labs.py` - New lab results endpoints
- ✅ `api/v1/symptoms.py` - New symptoms endpoints
- ✅ `api/v1/insights.py` - New insights endpoints
- ✅ `api/v1/assessments.py` - Updated to use new structure
- ✅ `api/v1/protocols.py` - Updated to use new structure
- ✅ `api/v1/wearables.py` - Updated imports

### 3. Configuration Unified
- ✅ `app/config/settings.py` - Single source of truth
- ✅ `app/config/security.py` - JWT & password hashing
- ✅ `app/config/logging.py` - Logging setup
- ✅ All config imports updated in main.py, database.py, RAG engine

### 4. Domain Models Created
- ✅ `domain/models/user.py`
- ✅ `domain/models/lab_result.py`
- ✅ `domain/models/wearable_sample.py`
- ✅ `domain/models/symptom.py`
- ✅ `domain/models/questionnaire.py`
- ✅ `domain/models/insight.py`
- ✅ `domain/models/protocol.py`
- ✅ `domain/models/health_data_point.py` (legacy compatibility)

### 5. Domain Schemas Created
- ✅ All corresponding Pydantic schemas in `domain/schemas/`

### 6. Engine Structure
- ✅ Analytics layer: time_series, correlation, rolling_metrics
- ✅ Reasoning layer: dysfunction_detector, protocol_generator
- ✅ RAG layer: retriever.py (updated imports)
- ✅ Prompts: insight_prompt.txt, protocol_prompt.txt

## 🔄 In Progress / Needs Attention

### Import Updates Still Needed
These files still reference old import paths and need updating:

1. **Services**
   - `app/services/wearable_service.py` - Uses `app.models.database.HealthDataPoint`
   - `app/services/dysfunction_detector.py` - Old copy, should use engine version

2. **Utils**
   - `app/utils/compliance.py` - Uses old model imports
   - `app/utils/validators.py` - May need updates
   - `app/utils/validation.py` - May need updates

3. **Legacy API Files** (can be removed after migration)
   - `app/api/health_data.py` - Old endpoint, should migrate to v1
   - `app/api/users.py` - Old version, replaced by v1
   - `app/api/assessments.py` - Old version, replaced by v1
   - `app/api/protocols.py` - Old version, replaced by v1
   - `app/api/wearables.py` - Old version, replaced by v1

4. **Legacy Models** (can be removed after migration)
   - `app/models/database.py` - Old models, replaced by domain models
   - `app/models/schemas.py` - Old schemas, replaced by domain schemas

### Missing Components

1. **Engine Components**
   - ⏳ `engine/rag/embedder.py` - Embedding utilities
   - ⏳ `engine/rag/knowledge_loader.py` - Knowledge base loader
   - ⏳ `engine/reasoning/insight_generator.py` - Generate insights from analytics
   - ⏳ `engine/reasoning/summariser.py` - Summarize health data

2. **Services**
   - ⏳ `services/onboarding_service.py` - User onboarding flow
   - ⏳ `services/ingestion_service.py` - Data ingestion pipeline
   - ⏳ `services/insight_service.py` - Insight generation service
   - ⏳ `services/protocol_service.py` - Protocol management service

3. **Repositories** (Data Access Layer)
   - ⏳ `domain/repositories/user_repo.py`
   - ⏳ `domain/repositories/lab_repo.py`
   - ⏳ `domain/repositories/wearable_repo.py`
   - ⏳ `domain/repositories/symptom_repo.py`
   - ⏳ `domain/repositories/insight_repo.py`
   - ⏳ `domain/repositories/protocol_repo.py`

## ⏳ Pending - Frontend Restructure

### Current Structure
```
frontend/src/
  ├── api/          ✅ (exists)
  ├── components/   ✅ (exists)
  ├── pages/        ✅ (exists)
  └── services/     ✅ (exists)
```

### Target Structure
```
frontend/src/
  ├── app/
  │   ├── layout.tsx
  │   ├── globals.css
  │   └── router.tsx
  ├── pages/
  │   ├── index.tsx
  │   ├── onboarding/
  │   │   ├── questions.tsx
  │   │   └── profile.tsx
  │   └── dashboard/
  │       ├── index.tsx
  │       ├── insights.tsx
  │       ├── trends.tsx
  │       └── protocols.tsx
  ├── components/
  │   ├── ui/        (Button, Card, Input, Toggle, Tabs)
  │   ├── insights/
  │   ├── charts/
  │   └── layout/
  ├── state/
  │   ├── userStore.ts
  │   ├── healthDataStore.ts
  │   └── insightStore.ts
  ├── api/
  │   ├── client.ts
  │   ├── users.ts
  │   ├── insights.ts
  │   ├── labs.ts
  │   └── wearables.ts
  └── lib/
      ├── formatters.ts
      ├── converters.ts
      └── validation.ts
```

## ⏳ Pending - Tests Restructure

### Target Structure
```
tests/
  ├── unit/
  │   ├── domain/
  │   ├── engine/
  │   └── services/
  ├── integration/
  │   ├── api/
  │   └── ingestion/
  └── e2e/
      └── full assessment → insight → protocol
```

## Next Steps

### Immediate (Backend)
1. Update remaining imports in services and utils
2. Remove or migrate legacy API files
3. Create missing engine components
4. Create repository layer

### Short-term (Frontend)
1. Restructure frontend directory
2. Create new page components
3. Create UI component library
4. Set up state management (Zustand stores)
5. Update API client files

### Medium-term (Tests)
1. Restructure test directory
2. Create unit tests for domain, engine, services
3. Create integration tests for API endpoints
4. Create E2E tests for full workflows

## Migration Commands

### To test the new structure:
```bash
cd backend
python3 -c "from app.config.settings import get_settings; print('Config OK')"
python3 -c "from app.domain.models import User; print('Models OK')"
python3 -c "from app.api.v1 import users; print('API OK')"
```

### To run the application:
```bash
cd backend
uvicorn app.main:app --reload
```

## Notes

- The old `app/models/` and `app/api/` (non-v1) directories can be removed after confirming all imports are updated
- HealthDataPoint is kept as a legacy model for backward compatibility
- All new code should use the new structure: `from app.domain.models.*`, `from app.config.settings import get_settings`, etc.

