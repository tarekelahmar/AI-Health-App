# Backend Restructure - Migration Status

## ✅ Completed

### Directory Structure
- ✅ Created `app/api/v1/` directory with all API endpoints
- ✅ Created `app/config/` with settings.py, security.py, logging.py
- ✅ Created `app/domain/models/` with all domain models
- ✅ Created `app/domain/schemas/` with all Pydantic schemas
- ✅ Created `app/engine/analytics/` with time_series, correlation, rolling_metrics
- ✅ Created `app/engine/reasoning/` (dysfunction_detector, protocol_generator moved)
- ✅ Created `app/engine/rag/` (rag_engine moved to retriever.py)

### Files Created/Updated
- ✅ `app/config/settings.py` - Single source of truth for configuration
- ✅ `app/config/security.py` - JWT and password hashing
- ✅ `app/config/logging.py` - Logging setup
- ✅ `app/api/v1/users.py` - Updated imports
- ✅ `app/api/v1/auth.py` - New authentication endpoints
- ✅ `app/api/v1/labs.py` - New lab results endpoints
- ✅ `app/api/v1/symptoms.py` - New symptoms endpoints
- ✅ `app/api/v1/insights.py` - New insights endpoints
- ✅ `app/api/v1/assessments.py` - Updated to use new structure
- ✅ `app/api/v1/protocols.py` - Updated to use new structure
- ✅ `app/api/v1/wearables.py` - Updated imports
- ✅ `app/main.py` - Updated to use new API structure
- ✅ `app/core/database.py` - Updated to use new config

## 🔄 In Progress

### Import Updates Needed
- ⚠️ `app/engine/reasoning/dysfunction_detector.py` - Still uses `app.models.database.HealthDataPoint`
- ⚠️ `app/engine/reasoning/protocol_generator.py` - May need import updates
- ⚠️ `app/engine/rag/retriever.py` - May need import updates
- ⚠️ `app/services/wearable_service.py` - May need import updates
- ⚠️ `app/utils/` files - May need import updates

### Legacy Models
- ⚠️ `HealthDataPoint` - Still referenced in dysfunction_detector
  - Options:
    1. Create `app/domain/models/health_data_point.py`
    2. Update detector to use WearableSample + LabResult
    3. Keep as legacy model temporarily

## ⏳ Pending

### Engine Structure
- ⏳ Create `app/engine/prompts/` with prompt templates
- ⏳ Create `app/engine/reasoning/insight_generator.py`
- ⏳ Create `app/engine/reasoning/summariser.py`
- ⏳ Create `app/engine/rag/embedder.py`
- ⏳ Create `app/engine/rag/knowledge_loader.py`

### Services
- ⏳ Create `app/services/onboarding_service.py`
- ⏳ Create `app/services/ingestion_service.py`
- ⏳ Create `app/services/insight_service.py`
- ⏳ Create `app/services/protocol_service.py`
- ⏳ Update `app/services/wearable_service.py` imports

### Repositories
- ⏳ Create `app/domain/repositories/user_repo.py`
- ⏳ Create `app/domain/repositories/lab_repo.py`
- ⏳ Create `app/domain/repositories/wearable_repo.py`
- ⏳ Create `app/domain/repositories/symptom_repo.py`
- ⏳ Create `app/domain/repositories/insight_repo.py`
- ⏳ Create `app/domain/repositories/protocol_repo.py`

### Utils
- ⏳ Update `app/utils/validators.py` imports
- ⏳ Update `app/utils/compliance.py` imports
- ⏳ Update `app/utils/transformers.py` imports
- ⏳ Update `app/utils/validation.py` imports

### Tests
- ⏳ Restructure tests into `unit/`, `integration/`, `e2e/`
- ⏳ Update test imports

## Import Migration Map

### Old → New
```python
# Config
from app.config import get_settings
→ from app.config.settings import get_settings

from app.utils.security import ...
→ from app.config.security import ...

# Models
from app.models.database import User
→ from app.domain.models.user import User

from app.models.schemas import UserCreate
→ from app.domain.schemas.user import UserCreate

# Database
from app.database import get_db
→ from app.core.database import get_db

# Services → Engine
from app.services.dysfunction_detector import DysfunctionDetector
→ from app.engine.reasoning.dysfunction_detector import DysfunctionDetector

from app.services.protocol_generator import ProtocolGenerator
→ from app.engine.reasoning.protocol_generator import ProtocolGenerator

from app.services.rag_engine import HealthRAGEngine
→ from app.engine.rag.retriever import HealthRAGEngine
```

## Next Steps

1. **Fix HealthDataPoint dependency** - Create domain model or update detector
2. **Update all remaining imports** in engine, services, utils
3. **Create missing engine components** (prompts, embedder, etc.)
4. **Create repositories** for data access layer
5. **Restructure frontend**
6. **Restructure tests**

