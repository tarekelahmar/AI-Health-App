# API Documentation

## Overview

The Health App API provides endpoints for managing users, health data, assessments, and protocols.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, authentication is not implemented. User ID is passed as a parameter.

## Endpoints

### Users

- `POST /users/` - Create a new user
- `GET /users/{user_id}` - Get user by ID

### Health Data

- `POST /health-data/` - Add a single health data point
- `POST /health-data/batch/` - Upload multiple data points from CSV
- `GET /health-data/{user_id}` - Get all health data for a user

### Assessments

- `POST /assess/{user_id}` - Run comprehensive health assessment

### Protocols

- `POST /protocol/{user_id}` - Generate weekly protocol

### Health Check

- `GET /` - API health check
- `GET /health/` - Database connection check

## Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

