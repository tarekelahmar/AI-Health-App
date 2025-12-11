# Test Structure

## Overview

Tests are organized into three layers:

1. **Unit Tests** (`tests/unit/`) - Test individual components in isolation
2. **Integration Tests** (`tests/integration/`) - Test components working together
3. **E2E Tests** (`tests/e2e/`) - Test complete user workflows

## Directory Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── unit/                    # Unit tests
│   ├── domain/             # Domain models and schemas
│   ├── engine/             # Engine components (analytics, reasoning, RAG)
│   ├── services/           # Service layer
│   └── utils/               # Utility functions
├── integration/             # Integration tests
│   ├── api/                 # API endpoint tests
│   └── repositories/        # Repository layer tests
└── e2e/                     # End-to-end tests
    └── test_full_health_flow.py
```

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run specific test layer
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# E2E tests only
pytest tests/e2e/
```

### Run with coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run specific test file
```bash
pytest tests/unit/domain/test_models.py
```

## Test Categories

### Unit Tests

**Domain Tests** (`tests/unit/domain/`)
- `test_models.py` - Test domain models (User, Insight, Protocol, etc.)
- `test_schemas.py` - Test Pydantic schemas

**Engine Tests** (`tests/unit/engine/`)
- `test_dysfunction_detector.py` - Test dysfunction detection logic
- `test_analytics.py` - Test analytics functions (time series, correlation, etc.)
- `test_rag_engine.py` - Test RAG retrieval (mocked)

**Service Tests** (`tests/unit/services/`)
- Test service layer in isolation with mocked dependencies

**Utils Tests** (`tests/unit/utils/`)
- Test utility functions (validators, formatters, etc.)

### Integration Tests

**API Tests** (`tests/integration/api/`)
- `test_users.py` - User API endpoints
- `test_health_data.py` - Health data API endpoints
- `test_assessments.py` - Assessment API endpoints
- Tests use real database (SQLite in-memory) and real dependencies

**Repository Tests** (`tests/integration/repositories/`)
- `test_user_repo.py` - User repository CRUD operations
- `test_health_data_repo.py` - Health data repository operations
- Tests repository layer with real database

### E2E Tests

**Full Flow Tests** (`tests/e2e/`)
- `test_full_health_flow.py` - Complete user journey:
  1. User registration
  2. Add health data
  3. Run assessment
  4. Generate insights
  5. Generate protocol
  6. Track progress

## Test Fixtures

Shared fixtures are defined in `conftest.py`:

- `db` - Database session fixture (SQLite in-memory)
- `client` - FastAPI TestClient fixture

## Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_something():
    pass

@pytest.mark.integration
def test_api_endpoint():
    pass

@pytest.mark.e2e
def test_full_flow():
    pass
```

## Notes

- **Placeholder tests** exist for components not yet implemented (repositories, some engine components)
- These will be filled in as the codebase evolves
- All tests use in-memory SQLite for speed and isolation
- E2E tests may require additional setup (API keys, etc.)

