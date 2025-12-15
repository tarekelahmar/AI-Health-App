.PHONY: backend frontend dev-up dev-down test lint

dev-up:
	cd backend && docker compose -f docker-compose.dev.yml up -d

dev-down:
	cd backend && docker compose -f docker-compose.dev.yml down -v

backend:
	cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && PYTHONPATH=. pytest -q

lint:
	cd backend && python -m compileall app

