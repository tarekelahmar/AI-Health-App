.PHONY: help migrate-create migrate-upgrade migrate-downgrade migrate-current migrate-history migrate-init

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

migrate-create: ## Create a new migration (usage: make migrate-create MESSAGE="your message")
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required"; \
		echo "Usage: make migrate-create MESSAGE=\"your migration message\""; \
		exit 1; \
	fi
	alembic revision --autogenerate -m "$(MESSAGE)"

migrate-upgrade: ## Apply all pending migrations
	alembic upgrade head

migrate-downgrade: ## Rollback one migration (usage: make migrate-downgrade REVISION="-1")
	@REVISION=$${REVISION:-"-1"}; \
	alembic downgrade $$REVISION

migrate-current: ## Show current migration version
	alembic current

migrate-history: ## Show migration history
	alembic history

migrate-init: ## Initialize database with migrations (first time setup)
	alembic upgrade head

