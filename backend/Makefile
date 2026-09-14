.PHONY: install dev migrate seed lint typecheck test build check

install:
	uv sync --locked

dev:
	uv run --no-sync python manage.py runserver 127.0.0.1:8000

migrate:
	uv run --no-sync python manage.py migrate

seed:
	uv run --no-sync python manage.py seed_dev

lint:
	uv run --no-sync ruff check .
	uv run --no-sync ruff format --check .

typecheck:
	uv run --no-sync mypy

test:
	uv run --no-sync pytest

build:
	uv build

check: lint typecheck test build
	uv run --no-sync python manage.py check
