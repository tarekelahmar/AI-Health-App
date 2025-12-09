# Project Structure

This document describes the reorganized project structure.

## Directory Layout

```
health-app/
├── backend/                    # Backend application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py          # Backward compatibility (imports from core.config)
│   │   ├── dependencies.py     # Shared FastAPI dependencies
│   │   ├── main.py            # FastAPI application entry point
│   │   ├── database.py        # Moved to core/database.py
│   │   ├── data_generator.py  # Sample data generation
│   │   │
│   │   ├── api/               # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── users.py
│   │   │   ├── health_data.py
│   │   │   ├── assessments.py (renamed from assessment.py)
│   │   │   ├── protocols.py  (renamed from protocol.py)
│   │   │   └── wearables.py   # NEW: Wearable integrations
│   │   │
│   │   ├── models/            # Database models and schemas
│   │   │   ├── __init__.py
│   │   │   ├── database.py    # SQLAlchemy models (renamed from models.py)
│   │   │   └── schemas.py     # Pydantic schemas
│   │   │
│   │   ├── services/          # Business logic services
│   │   │   ├── __init__.py
│   │   │   ├── rag_engine.py
│   │   │   ├── dysfunction_detector.py
│   │   │   ├── protocol_generator.py
│   │   │   ├── wearable_service.py    # NEW
│   │   │   └── notification_service.py # NEW: Email/SMS alerts
│   │   │
│   │   ├── utils/             # Utility functions
│   │   │   ├── __init__.py
│   │   │   ├── validators.py  # Data validation (imports from validation.py)
│   │   │   ├── validation.py  # Original validation logic
│   │   │   ├── transformers.py # NEW: Data unit conversion
│   │   │   ├── security.py    # NEW: Auth, encryption
│   │   │   └── logging.py      # NEW: Structured logging
│   │   │
│   │   ├── core/              # Core configuration
│   │   │   ├── __init__.py
│   │   │   ├── config.py      # Application configuration
│   │   │   ├── database.py    # Database connection
│   │   │   └── health_ontology.json # Moved from root
│   │   │
│   │   └── migrations/        # Database migrations (Alembic)
│   │       └── versions/
│   │
│   ├── tests/                 # Test suite
│   │   ├── __init__.py
│   │   ├── conftest.py        # Pytest fixtures
│   │   ├── test_api/
│   │   │   ├── test_users.py
│   │   │   ├── test_health_data.py
│   │   │   └── test_assessments.py
│   │   ├── test_services/
│   │   │   ├── test_rag_engine.py
│   │   │   └── test_dysfunction_detector.py
│   │   └── test_utils/
│   │       └── test_validators.py
│   │
│   ├── knowledge_base/        # Knowledge base documents
│   │   ├── protocols.md
│   │   └── evidence_base/     # NEW: Organized by system
│   │       ├── sleep/
│   │       ├── metabolic/
│   │       └── stress_response/
│   │
│   ├── requirements.txt
│   ├── requirements-dev.txt  # NEW: Development dependencies
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── env.example
│   └── alembic.ini            # NEW: Database migrations config
│
├── frontend/                   # NEW: Frontend application (placeholder)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   ├── package.json
│   └── Dockerfile
│
├── docs/                       # NEW: Documentation
│   ├── API.md
│   ├── DEPLOYMENT.md
│   ├── COMPLIANCE.md
│   └── CONTRIBUTING.md
│
├── docker-compose.prod.yml    # NEW: Production Docker Compose
├── .github/
│   └── workflows/              # CI/CD pipelines
│       ├── ci.yml
│       ├── cd.yml
│       └── docker-build.yml
│
└── README.md

```

## Key Changes

1. **Backend Structure**: All backend code moved to `backend/` directory
2. **Models Separation**: `models.py` and `schemas.py` moved to `app/models/` directory
3. **API Organization**: API endpoints organized in `app/api/` with clear naming
4. **New Services**: Added `wearable_service.py` and `notification_service.py`
5. **New Utils**: Added `transformers.py`, `security.py`, and `logging.py`
6. **Configuration**: Centralized in `app/core/config.py`
7. **Documentation**: Added comprehensive docs in `docs/` directory
8. **Testing**: Reorganized tests with proper structure and fixtures

## Import Updates

All imports have been updated to use the new structure:
- `from app import models` → `from app.models.database import User, HealthDataPoint`
- `from app import schemas` → `from app.models.schemas import UserCreate, UserResponse`
- `app.api.assessment` → `app.api.assessments`
- `app.api.protocol` → `app.api.protocols`

## Running the Application

From the `backend/` directory:
```bash
uvicorn app.main:app --reload
```

Or using Docker:
```bash
cd backend
docker-compose up
```

