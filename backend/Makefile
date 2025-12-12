.PHONY: help dev test lint migrate migrate-create migrate-upgrade migrate-downgrade migrate-current migrate-history migrate-init install seed clean

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development
install: ## Install dependencies
	@echo "📦 Installing dependencies..."
	@cd .. && python -m venv venv 2>/dev/null || true
	@cd .. && source venv/bin/activate && pip install --upgrade pip && pip install -r backend/requirements.txt
	@echo "✅ Dependencies installed"

dev: ## Start development server (API + deps)
	@echo "🚀 Starting development server..."
	@if [ ! -f ../.env ] && [ ! -f .env ]; then \
		echo "⚠️  No .env file found. Creating from .env.example..."; \
		cp env.example .env 2>/dev/null || echo "⚠️  Please create .env file manually"; \
	fi
	@cd .. && source venv/bin/activate && cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Testing
test: ## Run tests
	@echo "🧪 Running tests..."
	@cd .. && source venv/bin/activate && cd backend && pytest tests/ -v --cov=app --cov-report=term-missing

test-unit: ## Run unit tests only
	@echo "🧪 Running unit tests..."
	@cd .. && source venv/bin/activate && cd backend && pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo "🧪 Running integration tests..."
	@cd .. && source venv/bin/activate && cd backend && pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests only
	@echo "🧪 Running e2e tests..."
	@cd .. && source venv/bin/activate && cd backend && pytest tests/e2e/ -v

# Linting
lint: ## Run linting checks
	@echo "🔍 Running linting checks..."
	@cd .. && source venv/bin/activate && cd backend && \
		python -m flake8 app tests --max-line-length=120 --exclude=venv,__pycache__ || \
		(echo "⚠️  flake8 not installed. Install with: pip install flake8" && exit 0)

format: ## Format code with black (if available)
	@echo "✨ Formatting code..."
	@cd .. && source venv/bin/activate && cd backend && \
		python -m black app tests --line-length=120 2>/dev/null || \
		(echo "⚠️  black not installed. Install with: pip install black" && exit 0)

# Database migrations
migrate: migrate-upgrade ## Alias for migrate-upgrade

migrate-create: ## Create a new migration (usage: make migrate-create MESSAGE="your message")
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required"; \
		echo "Usage: make migrate-create MESSAGE=\"your migration message\""; \
		exit 1; \
	fi
	@cd .. && source venv/bin/activate && cd backend && alembic revision --autogenerate -m "$(MESSAGE)"

migrate-upgrade: ## Apply all pending migrations
	@echo "📊 Applying database migrations..."
	@cd .. && source venv/bin/activate && cd backend && alembic upgrade head

migrate-downgrade: ## Rollback one migration (usage: make migrate-downgrade REVISION="-1")
	@REVISION=$${REVISION:-"-1"}; \
	cd .. && source venv/bin/activate && cd backend && alembic downgrade $$REVISION

migrate-current: ## Show current migration version
	@cd .. && source venv/bin/activate && cd backend && alembic current

migrate-history: ## Show migration history
	@cd .. && source venv/bin/activate && cd backend && alembic history

migrate-init: ## Initialize database with migrations (first time setup)
	@echo "📊 Initializing database..."
	@cd .. && source venv/bin/activate && cd backend && alembic upgrade head

# Data seeding
seed: ## Seed demo data (idempotent)
	@echo "🌱 Seeding demo data..."
	@cd .. && source venv/bin/activate && cd backend && PYTHONPATH=. python scripts/seed_demo_data.py

# Cleanup
clean: ## Clean up generated files
	@echo "🧹 Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"

clean-test: ## Clean test database
	@echo "🧹 Cleaning test database..."
	@rm -f test.db
	@echo "✅ Test database cleaned"
