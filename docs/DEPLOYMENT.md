# Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Supabase account and database
- OpenAI API key

## Local Development

1. Clone the repository
2. Copy `env.example` to `.env` and configure
3. Run with docker-compose:
   ```bash
   docker-compose up -d
   ```

## Production Deployment

### Using Docker

1. Build the image:
   ```bash
   docker build -t health-app:latest .
   ```

2. Run the container:
   ```bash
   docker run -d \
     -p 8000:8000 \
     --env-file .env \
     health-app:latest
   ```

### Using Docker Compose

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Environment Variables

See `env.example` for all required environment variables.

## Database Migrations

Run migrations with Alembic:
```bash
cd backend
alembic upgrade head
```

## Monitoring

- Health check: `http://your-domain/health/`
- API docs: `http://your-domain/docs`

