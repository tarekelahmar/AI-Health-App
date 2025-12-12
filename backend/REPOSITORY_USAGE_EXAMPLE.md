# Repository Usage Pattern in FastAPI

## Dependency Injection Pattern

All repositories are available via FastAPI dependency injection through `app.dependencies`.

## Example Usage

### In API Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException
from app.domain.models.user import User
from app.config.security import get_current_user
from app.dependencies import get_user_repo, get_insight_repo
from app.domain.repositories import UserRepository, InsightRepository

router = APIRouter()

@router.get("/users/me")
def get_me(
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """Get current user's profile using repository"""
    db_user = user_repo.get_by_id(current_user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.get("/insights")
def list_insights(
    current_user: User = Depends(get_current_user),
    insight_repo: InsightRepository = Depends(get_insight_repo),
):
    """List user's insights using repository"""
    insights = insight_repo.list_for_user(
        user_id=current_user.id,
        limit=20
    )
    return insights
```

### In Services

```python
from app.domain.repositories import HealthDataRepository, WearableRepository
from app.core.database import get_db

def sync_wearable_data(user_id: int):
    """Service function using repositories"""
    db = next(get_db())
    health_repo = HealthDataRepository(db)
    wearable_repo = WearableRepository(db)
    
    # Use repositories for data access
    recent_data = health_repo.get_recent(user_id=user_id, days=7)
    # ... process data
```

## Available Repository Dependencies

- `get_user_repo()` → `UserRepository`
- `get_lab_repo()` → `LabResultRepository`
- `get_wearable_repo()` → `WearableRepository`
- `get_symptom_repo()` → `SymptomRepository`
- `get_questionnaire_repo()` → `QuestionnaireRepository`
- `get_insight_repo()` → `InsightRepository`
- `get_protocol_repo()` → `ProtocolRepository`
- `get_health_data_repo()` → `HealthDataRepository`

## Benefits

1. **Clean separation**: API layer doesn't directly query database
2. **Testability**: Easy to mock repositories in tests
3. **Consistency**: All data access goes through same pattern
4. **Type safety**: Full type hints for better IDE support

