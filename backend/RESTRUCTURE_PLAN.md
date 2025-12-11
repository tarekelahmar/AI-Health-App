# Backend Restructure Plan

## New Directory Structure

```
backend/app/
  api/
    v1/
      users.py ✅
      auth.py (to be created)
      labs.py (to be created)
      wearables.py ✅
      symptoms.py (to be created)
      assessments.py ✅
      insights.py (to be created)
      protocols.py ✅
  config/
    settings.py ✅
    logging.py ✅
    security.py ✅
  core/
    database.py
    migrations/
    health_ontology.json
  domain/
    models/ ✅ (created)
    schemas/ (to be created)
    repositories/ (to be created)
  engine/
    rag/
    analytics/
    reasoning/
    prompts/
  services/
  utils/
  main.py
```

## Migration Status

### ✅ Completed
- Created new directory structure
- Created config/settings.py, config/security.py, config/logging.py
- Created domain/models/*.py files
- Copied API files to api/v1/

### 🔄 In Progress
- Updating imports in API files
- Creating domain schemas
- Creating engine structure
- Moving services to new locations

### ⏳ Pending
- Update all imports throughout codebase
- Create repositories
- Restructure frontend
- Restructure tests

## Import Updates Needed

### Old → New
- `from app.config import get_settings` → `from app.config.settings import get_settings`
- `from app.utils.security import ...` → `from app.config.security import ...`
- `from app.models.database import User` → `from app.domain.models.user import User`
- `from app.models.schemas import ...` → `from app.domain.schemas.* import ...`
- `from app.services.dysfunction_detector import ...` → `from app.engine.reasoning.dysfunction_detector import ...`

