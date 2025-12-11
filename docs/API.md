# API Documentation

## Overview

The Health App API provides endpoints for managing users, health data, assessments, protocols, and wearable integrations.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Most endpoints require authentication via Bearer token.

### Authentication Endpoints

- `POST /api/v1/users/login` - User login (returns access token)
- `GET /api/v1/users/me` - Get current user profile (requires authentication)

**Example:**
```bash
# Login
curl -X POST "http://localhost:8000/api/v1/users/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=yourpassword"

# Use token
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer <access_token>"
```

## Endpoints

### Users

- `POST /api/v1/users/` - Create a new user
  - Request body: `{ "name": "John Doe", "email": "john@example.com", "password": "securepassword" }`
  - Returns: User object (password excluded)
  
- `GET /api/v1/users/{user_id}` - Get user by ID
  - Returns: User object
  
- `GET /api/v1/users/` - List all users (admin only)
  - Returns: List of user objects
  
- `POST /api/v1/users/login` - User login
  - Request: Form data with `username` (email) and `password`
  - Returns: `{ "access_token": "...", "token_type": "bearer" }`
  
- `GET /api/v1/users/me` - Get current user profile (authenticated)
  - Requires: `Authorization: Bearer <token>` header
  - Returns: Current user object

### Health Data

- `POST /api/v1/health-data/?user_id={user_id}` - Add a single health data point
  - Request body: `{ "data_type": "sleep_duration", "value": 7.5, "unit": "hours", "source": "wearable" }`
  - Returns: Created health data point
  
- `POST /api/v1/health-data/batch/?user_id={user_id}` - Upload multiple data points from CSV
  - Request: CSV file path
  - Returns: `{ "status": "success", "rows_uploaded": 10 }`
  
- `GET /api/v1/health-data/{user_id}` - Get all health data for a user
  - Returns: List of health data points

### Assessments

- `POST /api/v1/assessments/{user_id}` - Run comprehensive health assessment
  - Returns: Assessment with detected dysfunctions and RAG insights
  - Response: `{ "user_id": 1, "assessment_ids": [...], "dysfunctions": [...], "rag_insights": {...}, "timestamp": "..." }`
  
- `GET /api/v1/assessments/{user_id}` - Get user's latest assessment
  - Returns: Latest health assessment

### Protocols

- `POST /api/v1/protocols/{user_id}` - Generate weekly protocol based on latest assessment
  - Returns: Personalized protocol with interventions
  - Response: `{ "user_id": 1, "week": 1, "start_date": "...", "interventions": [...] }`

### Wearables

- `POST /api/v1/wearables/sync` - Trigger manual wearable data sync (authenticated)
  - Requires: `Authorization: Bearer <token>` header
  - Returns: `{ "status": "syncing", "user_id": 1 }`
  
- `POST /api/v1/wearables/connect/{wearable}` - OAuth callback for wearable connection (authenticated)
  - Parameters: `wearable` (e.g., "fitbit", "oura"), `code` (OAuth code)
  - Returns: `{ "status": "connected", "wearable": "fitbit" }`

### Health Check

- `GET /` - API root endpoint
  - Returns: API information
  
- `GET /health` - Health check endpoint
  - Returns: `{ "status": "healthy", "debug": false, "database": "connected" }`

## Response Format

All endpoints return JSON. Error responses follow this format:

```json
{
  "detail": "Error message"
}
```

## Status Codes

- `200` - Success
- `201` - Created (for POST requests that create resources)
- `400` - Bad Request (validation errors, missing parameters)
- `401` - Unauthorized (invalid or missing authentication token)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error

## Rate Limiting

Rate limiting may be applied in production. Check response headers for rate limit information.

## Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Versioning

The API is versioned using the `/api/v1/` prefix. Future versions will use `/api/v2/`, etc.
