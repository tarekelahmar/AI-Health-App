# System Map

**Health AI Coach - AI-Powered Functional Health Assessment Platform**

This document provides a comprehensive map of the system architecture, components, data flow, and dependencies.

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Component Map](#component-map)
4. [Data Flow](#data-flow)
5. [API Endpoints](#api-endpoints)
6. [External Dependencies](#external-dependencies)
7. [Data Models](#data-models)
8. [Key Services](#key-services)

---

## System Overview

The Health AI Coach is a FastAPI-based application that provides AI-powered functional health assessment and personalized protocol generation. The system follows Domain-Driven Design (DDD) principles with a clean, layered architecture.

### Core Capabilities

- **User Management**: Authentication, authorization, and user profiles
- **Health Data Collection**: Lab results, wearable device data, symptoms, questionnaires
- **AI-Powered Analysis**: Dysfunction detection, correlation analysis, insight generation
- **Protocol Generation**: Personalized health protocols based on assessments
- **RAG Engine**: Evidence-based recommendations using retrieval-augmented generation
- **Wearable Integration**: Support for Fitbit, Oura, and Whoop devices

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                   │
│  /api/v1/auth, /api/v1/users, /api/v1/insights, etc.    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              Application Services Layer                  │
│  NotificationService, WearableService, ProtocolService   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              Domain Layer (Business Logic)               │
│  Models, Repositories, Schemas                           │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              Engine Layer (AI & Analytics)               │
│  InsightEngine, ProtocolGenerator, RAG, Analytics       │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              Infrastructure Layer                        │
│  Database (PostgreSQL/SQLite), Vector DB (ChromaDB)     │
└─────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

1. **API Layer** (`app/api/v1/`)
   - HTTP request/response handling
   - Input validation
   - Authentication/authorization
   - Rate limiting
   - Error handling

2. **Application Services** (`app/services/`)
   - Orchestrate domain operations
   - Coordinate between multiple repositories
   - Handle cross-cutting concerns

3. **Domain Layer** (`app/domain/`)
   - **Models**: SQLAlchemy ORM entities
   - **Repositories**: Data access abstraction
   - **Schemas**: Pydantic validation schemas

4. **Engine Layer** (`app/engine/`)
   - **Analytics**: Time series, correlation, rolling metrics
   - **Reasoning**: AI-powered insight generation, dysfunction detection
   - **RAG**: Knowledge retrieval and evidence-based recommendations

5. **Infrastructure** (`app/core/`)
   - Database connection and session management
   - Configuration management
   - Logging setup

---

## Component Map

### API Endpoints (`app/api/v1/`)

| Component | Endpoints | Purpose |
|-----------|-----------|---------|
| `auth.py` | `/api/v1/auth/login`<br>`/api/v1/auth/me` | Authentication and user session management |
| `users.py` | `/api/v1/users/`<br>`/api/v1/users/{id}`<br>`/api/v1/users/me` | User CRUD operations |
| `labs.py` | `/api/v1/labs/` | Lab result management |
| `wearables.py` | `/api/v1/wearables/sync`<br>`/api/v1/wearables/connect/{device}` | Wearable device integration |
| `symptoms.py` | `/api/v1/symptoms/` | Symptom tracking |
| `assessments.py` | `/api/v1/assessments/{user_id}` | Health assessment generation |
| `insights.py` | `/api/v1/insights/sleep`<br>`/api/v1/insights/`<br>`/api/v1/insights/{id}` | AI-generated health insights |
| `protocols.py` | `/api/v1/protocols/{user_id}` | Personalized protocol generation |

### Domain Models (`app/domain/models/`)

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `User` | User accounts and profiles | id, email, name, hashed_password |
| `LabResult` | Laboratory test results | user_id, test_name, value, unit, timestamp |
| `WearableSample` | Wearable device data points | user_id, device_type, metric_type, value, timestamp |
| `Symptom` | User-reported symptoms | user_id, symptom_type, severity, timestamp |
| `Questionnaire` | Health questionnaires | user_id, responses, completed_at |
| `Insight` | AI-generated health insights | user_id, insight_type, title, description, confidence_score |
| `Protocol` | Personalized health protocols | user_id, protocol_type, recommendations |
| `HealthDataPoint` | Aggregated health metrics | user_id, metric_type, value, timestamp |

### Repositories (`app/domain/repositories/`)

Each repository provides a clean abstraction over data access:

- `UserRepository` - User CRUD operations
- `LabResultRepository` - Lab result queries and persistence
- `WearableRepository` - Wearable data queries
- `SymptomRepository` - Symptom tracking
- `QuestionnaireRepository` - Questionnaire management
- `InsightRepository` - Insight persistence and retrieval
- `ProtocolRepository` - Protocol storage
- `HealthDataRepository` - Aggregated health data

### AI Engines (`app/engine/`)

#### Analytics (`app/engine/analytics/`)

- **`correlation.py`**: Pearson correlation analysis between health metrics
- **`time_series.py`**: Time series data processing and alignment
- **`rolling_metrics.py`**: Rolling window calculations (mean, std, trends)

#### Reasoning (`app/engine/reasoning/`)

- **`insight_generator.py`**: Generates AI-powered health insights
  - Uses OpenAI GPT-4 for analysis
  - Integrates with RAG engine for evidence
  - Analyzes wearable data, lab results, symptoms
  
- **`dysfunction_detector.py`**: Detects health dysfunctions
  - Pattern recognition in health data
  - Severity assessment
  - Confidence scoring

- **`protocol_generator.py`**: Generates personalized protocols
  - Based on detected dysfunctions
  - Uses health ontology
  - Evidence-based recommendations

#### RAG (`app/engine/rag/`)

- **`retriever.py`**: Retrieval-Augmented Generation engine
  - Vector database (ChromaDB) for knowledge base
  - Semantic search over protocols and evidence
  - Context injection for LLM prompts

### Services (`app/services/`)

- **`notification_service.py`**: Email notifications for alerts
- **`wearable_service.py`**: Integration with wearable APIs (Fitbit, Oura, Whoop)
- **`protocol_generator.py`**: High-level protocol generation orchestration

### Configuration (`app/config/`)

- **`settings.py`**: Centralized configuration (Pydantic Settings)
- **`security.py`**: JWT authentication, password hashing
- **`rate_limiting.py`**: API rate limiting (slowapi)
- **`logging.py`**: Logging configuration

---

## Data Flow

### Insight Generation Flow

```
User Request
    │
    ▼
API Endpoint (/api/v1/insights/sleep)
    │
    ▼
InsightEngine.generate_sleep_insights()
    │
    ├─► WearableRepository.get_sleep_data()
    ├─► LabResultRepository.get_recent_labs()
    ├─► SymptomRepository.get_symptoms()
    │
    ▼
Analytics Layer
    ├─► TimeSeriesAnalysis
    ├─► CorrelationAnalysis
    └─► RollingMetrics
    │
    ▼
RAG Engine
    └─► Retrieve relevant evidence from knowledge base
    │
    ▼
OpenAI GPT-4
    └─► Generate insight with context
    │
    ▼
InsightRepository.save()
    │
    ▼
API Response
```

### Protocol Generation Flow

```
User Request
    │
    ▼
API Endpoint (/api/v1/protocols/{user_id})
    │
    ▼
ProtocolGenerator.generate_protocol()
    │
    ├─► InsightRepository.get_latest_dysfunctions()
    │
    ▼
DysfunctionDetector.assess_severity()
    │
    ▼
RAG Engine
    └─► Retrieve evidence-based protocols
    │
    ▼
OpenAI GPT-4
    └─► Generate personalized protocol
    │
    ▼
ProtocolRepository.save()
    │
    ▼
API Response
```

### Wearable Sync Flow

```
User Request (/api/v1/wearables/sync)
    │
    ▼
WearableService.sync_data()
    │
    ├─► Fitbit API / Oura API / Whoop API
    │
    ▼
Transform & Validate Data
    │
    ▼
WearableRepository.bulk_insert()
    │
    ▼
API Response
```

---

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login (OAuth2 password flow)
- `GET /api/v1/auth/me` - Get current user profile

### Users
- `POST /api/v1/users/` - Create user
- `GET /api/v1/users/` - List users
- `GET /api/v1/users/{user_id}` - Get user by ID
- `GET /api/v1/users/me` - Get current user

### Labs
- `GET /api/v1/labs/` - List lab results
- `POST /api/v1/labs/` - Create lab result

### Wearables
- `POST /api/v1/wearables/sync` - Sync wearable data
- `POST /api/v1/wearables/connect/{wearable}` - Connect wearable device

### Symptoms
- `GET /api/v1/symptoms/` - List symptoms
- `POST /api/v1/symptoms/` - Create symptom entry

### Assessments
- `POST /api/v1/assessments/{user_id}` - Generate health assessment
- `GET /api/v1/assessments/{user_id}` - Get latest assessment

### Insights
- `POST /api/v1/insights/sleep` - Generate sleep insights
- `GET /api/v1/insights/` - List insights
- `GET /api/v1/insights/{insight_id}` - Get insight by ID

### Protocols
- `POST /api/v1/protocols/{user_id}` - Generate personalized protocol

### System
- `GET /` - Root endpoint (API info)
- `GET /health` - Health check
- `GET /docs` - Swagger UI documentation
- `GET /openapi.json` - OpenAPI schema

---

## External Dependencies

### Databases

- **PostgreSQL** (production) / **SQLite** (development)
  - Primary data store for all domain models
  - Managed via SQLAlchemy ORM
  - Migrations via Alembic

- **ChromaDB** (vector database)
  - Stores embeddings for knowledge base
  - Used by RAG engine for semantic search
  - Location: `./chroma_db/`

### External APIs

- **OpenAI API**
  - GPT-4 for insight generation
  - GPT-4 for protocol generation
  - text-embedding-ada-002 for embeddings

- **Wearable Device APIs**
  - Fitbit API
  - Oura API
  - Whoop API

### Infrastructure Services

- **Redis** (optional)
  - Caching
  - Session storage
  - Rate limiting storage (if not using in-memory)

---

## Data Models

### User
```python
- id: int (PK)
- email: str (unique)
- name: str
- hashed_password: str
- created_at: datetime
```

### LabResult
```python
- id: int (PK)
- user_id: int (FK -> User)
- test_name: str
- value: float
- unit: str
- reference_range: str
- timestamp: datetime
- lab_name: str
```

### WearableSample
```python
- id: int (PK)
- user_id: int (FK -> User)
- device_type: str (fitbit, oura, whoop)
- metric_type: str (sleep_duration, hrv, steps, etc.)
- value: float
- unit: str
- timestamp: datetime
- device_id: str
```

### Insight
```python
- id: int (PK)
- user_id: int (FK -> User)
- insight_type: str (dysfunction, sleep, metabolic, etc.)
- title: str
- description: str
- confidence_score: float
- metadata: JSON
- generated_at: datetime
```

### Protocol
```python
- id: int (PK)
- user_id: int (FK -> User)
- protocol_type: str
- recommendations: JSON
- generated_at: datetime
```

---

## Key Services

### InsightEngine

**Location**: `app/engine/reasoning/insight_generator.py`

**Responsibilities**:
- Generate AI-powered health insights
- Analyze wearable data, lab results, symptoms
- Use RAG for evidence-based recommendations
- Persist insights to database

**Dependencies**:
- LabResultRepository
- WearableRepository
- HealthDataRepository
- SymptomRepository
- InsightRepository
- RAG Engine
- OpenAI API

### ProtocolGenerator

**Location**: `app/engine/reasoning/protocol_generator.py`

**Responsibilities**:
- Generate personalized health protocols
- Use dysfunction detection results
- Reference health ontology
- Provide evidence-based recommendations

**Dependencies**:
- InsightRepository
- DysfunctionDetector
- RAG Engine
- Health Ontology JSON

### DysfunctionDetector

**Location**: `app/engine/reasoning/dysfunction_detector.py`

**Responsibilities**:
- Detect health dysfunctions from data patterns
- Assess severity levels
- Calculate confidence scores
- Prioritize dysfunctions

**Dependencies**:
- Analytics modules (correlation, time series)
- Health data repositories

### RAG Engine

**Location**: `app/engine/rag/retriever.py`

**Responsibilities**:
- Semantic search over knowledge base
- Retrieve relevant evidence for protocols
- Generate context for LLM prompts

**Dependencies**:
- ChromaDB (vector database)
- OpenAI Embeddings API
- Knowledge base files (`knowledge_base/`)

---

## Configuration Management

### Settings (`app/config/settings.py`)

Centralized configuration using Pydantic Settings:

- **Environment**: development, staging, production
- **Database**: Connection strings, pool settings
- **OpenAI**: API keys, model selection
- **Security**: JWT secrets, token expiration
- **CORS**: Allowed origins, methods, headers
- **Feature Flags**: Enable/disable features
- **Rate Limiting**: Per-endpoint limits

### Environment Files

- `.env.example` - Template with all settings
- `.env.dev` - Development defaults
- `.env.staging` - Staging template
- `.env.prod` - Production template

---

## Security

### Authentication
- OAuth2 password flow
- JWT tokens (access + refresh)
- Password hashing with bcrypt

### Authorization
- Role-based access control (future)
- User-scoped data access
- API key authentication for services

### Rate Limiting
- IP-based limiting (slowapi)
- User-based limiting (authenticated)
- Configurable per endpoint

### Data Protection
- Input validation (Pydantic)
- SQL injection prevention (SQLAlchemy ORM)
- XSS protection (FastAPI defaults)

---

## Testing Structure

```
tests/
├── unit/              # Unit tests for individual components
│   ├── domain/        # Model and schema tests
│   ├── engine/        # Engine logic tests
│   └── api/           # API endpoint tests
├── integration/       # Integration tests
│   ├── test_api.py    # Full API flow tests
│   └── ...            # Service integration tests
└── e2e/               # End-to-end tests
    └── test_full_health_flow.py
```

---

## Knowledge Base

**Location**: `knowledge_base/`

- **`protocols.md`**: Evidence-based health protocols
- **`evidence_base/`**: Structured evidence by category
  - `metabolic/` - Metabolic health protocols
  - `sleep/` - Sleep optimization protocols
  - `stress_response/` - Stress management protocols

Used by RAG engine for retrieval-augmented generation.

---

## Deployment Architecture

### Development
- SQLite database
- In-memory rate limiting
- Local ChromaDB
- Hot reload enabled

### Production
- PostgreSQL database
- Redis for caching/rate limiting
- Persistent ChromaDB
- Docker containerization
- Environment-based configuration

---

## Key Design Patterns

1. **Repository Pattern**: Data access abstraction
2. **Dependency Injection**: FastAPI Depends() for services
3. **Factory Pattern**: Engine creation with dependencies
4. **Strategy Pattern**: Different analytics strategies
5. **Observer Pattern**: Event-driven notifications (future)

---

## Future Enhancements

- Real-time WebSocket connections for live data
- GraphQL API alternative
- Microservices architecture for scale
- Event sourcing for audit trails
- Advanced ML models for prediction
- Multi-tenant support
- Mobile app SDK

---

**Last Updated**: 2025-12-12  
**Version**: 1.0.0  
**Maintainer**: Development Team

