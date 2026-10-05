.PHONY: install dev test lint format typecheck db-up db-migrate services-up services-down

install:
	uv sync
	cd apps/web && npm install

dev:
	uv run uvicorn apps.api.app.main:app --reload

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy .

db-up:
	docker compose up -d db

db-migrate:
	uv run alembic upgrade head

services-up:
	docker compose up -d

services-down:
	docker compose down
