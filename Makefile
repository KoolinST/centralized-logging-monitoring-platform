.PHONY: help install run stop build test lint format clean logs shell

# ── Default target ────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  Centralized Logging & Monitoring Platform"
	@echo ""
	@echo "  Usage: make [target]"
	@echo ""
	@echo "  Setup"
	@echo "    install       Install dependencies"
	@echo "    env           Copy .env.example to .env"
	@echo ""
	@echo "  Development"
	@echo "    run           Start all services with Docker Compose"
	@echo "    stop          Stop all services"
	@echo "    restart       Restart all services"
	@echo "    build         Build Docker image"
	@echo "    logs          Tail logs from all services"
	@echo "    shell         Open a shell inside the flask_app container"
	@echo ""
	@echo "  Quality"
	@echo "    test          Run tests with coverage"
	@echo "    lint          Run flake8"
	@echo "    format        Run black"
	@echo "    check         Run lint + format check + tests"
	@echo ""
	@echo "  Cleanup"
	@echo "    clean         Remove containers, volumes, and cache"
	@echo "    clean-pyc     Remove Python cache files"
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────

install:
	pip install -r requirements-dev.txt

env:
	@if [ -f .env ]; then \
		echo ".env already exists — skipping."; \
	else \
		cp .env.example .env; \
		echo ".env created from .env.example. Fill in your values before running."; \
	fi

# ── Development ───────────────────────────────────────────────────────────────

run:
	docker compose up

run-detached:
	docker compose up -d

stop:
	docker compose down

restart:
	docker compose down && docker compose up

build:
	docker compose build --no-cache

logs:
	docker compose logs -f

logs-app:
	docker compose logs -f flask_app

shell:
	docker compose exec flask_app /bin/bash

# ── Quality ───────────────────────────────────────────────────────────────────

test:
	pytest --cov=app --cov-report=term-missing --cov-report=xml --junitxml=test-results/results.xml

test-fast:
	pytest -x --cov=app --cov-report=term-missing

lint:
	flake8 .

format:
	black .

format-check:
	black --check .

check: lint format-check test

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov coverage.xml coverage.svg

clean-pyc:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
