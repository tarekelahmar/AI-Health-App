# Quick Start Guide

## One-Command Setup

```bash
# From the backend directory
make install    # Install dependencies
make migrate     # Run database migrations
make seed        # Seed demo data (idempotent)
make dev         # Start development server
```

The server will be available at `http://localhost:8000` with API docs at `http://localhost:8000/docs`

## Environment Setup

1. Copy the appropriate environment template:
   ```bash
   cp .env.dev .env        # For development
   # OR
   cp .env.staging .env   # For staging
   # OR
   cp .env.prod .env      # For production
   ```

2. Edit `.env` with your actual values (database URL, API keys, etc.)

## Available Commands

- `make dev` - Start development server
- `make test` - Run all tests
- `make test-unit` - Run unit tests only
- `make test-integration` - Run integration tests only
- `make lint` - Run linting checks
- `make migrate` - Apply database migrations
- `make migrate-create MESSAGE="..."` - Create new migration
- `make seed` - Seed demo data (idempotent - safe to rerun)
- `make clean` - Clean up generated files
- `make help` - Show all available commands

## Verification Checklist

✅ Server starts cleanly: `make dev`  
✅ Tests pass: `make test`  
✅ Seed works (idempotent): `make seed` (run twice to verify)  
✅ API docs work: Visit `http://localhost:8000/docs`  

## Troubleshooting

- **Module not found errors**: Make sure you're in the backend directory and venv is activated
- **Database connection errors**: Check your `DATABASE_URL` in `.env`
- **Port already in use**: Kill the process on port 8000 or change the port in `uvicorn` command

