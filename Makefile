.PHONY: setup up down migrate ingest ingest-fixtures db-reset \
        test test-backend test-frontend lint format typecheck

setup:
	cp -n .env.example .env || true
	cd apps/api && uv sync
	cd apps/web && npm install

up:
	docker compose up -d postgres api web

down:
	docker compose down

migrate:
	cd apps/api && uv run alembic upgrade head

ingest:
	cd apps/api && uv run python -m app.ingestion.cli import --source ../../$(SOURCE)

ingest-fixtures:
	cd apps/api && uv run python -m app.ingestion.cli import --source ../../data/fixtures

db-reset:
	cd apps/api && uv run python -m app.ingestion.cli import --source ../../data/fixtures --reset

test: test-backend test-frontend

test-backend:
	cd apps/api && uv run pytest tests -v

test-frontend:
	cd apps/web && npm run test

lint:
	cd apps/api && uv run ruff check .
	cd apps/web && npm run lint

format:
	cd apps/api && uv run ruff format .
	cd apps/web && npm run format

typecheck:
	cd apps/api && uv run mypy app
	cd apps/web && npm run typecheck
