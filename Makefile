.PHONY: help install install-dev test test-cov lint format clean docker-build docker-run

# Default target
help:
	@echo "TheKnot Scraper - Available Commands:"
	@echo ""
	@echo "  install         - Install package in editable mode"
	@echo "  install-dev     - Install with development dependencies"
	@echo "  test            - Run unit tests"
	@echo "  test-cov        - Run tests with coverage report"
	@echo "  lint            - Run linters (ruff, mypy)"
	@echo "  format          - Format code with black"
	@echo "  clean           - Remove build artifacts and cache files"
	@echo "  docker-build    - Build Docker image"
	@echo "  docker-run      - Run scraper in Docker container"
	@echo "  validate        - Validate setup and dependencies"
	@echo ""

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=theknot_scraper --cov-report=html --cov-report=term

test-integration:
	cd theknot_scraper && python test_fetch_html.py

# Code quality
lint:
	ruff check theknot_scraper/ tests/
	mypy theknot_scraper/

format:
	black theknot_scraper/ tests/
	ruff check --fix theknot_scraper/ tests/

# Validation
validate:
	cd theknot_scraper && python validate_setup.py

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf build/ dist/ htmlcov/ .coverage

# Docker
docker-build:
	docker build \
		--build-arg BUILD_DATE=$$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
		--build-arg VERSION=1.0.0 \
		--build-arg VCS_REF=$$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
		-t theknot-scraper:latest .

docker-run:
	docker-compose up

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f scraper

# Development
dev-setup: install-dev
	mkdir -p output logs cookies
	cp theknot_scraper/.env.example theknot_scraper/.env 2>/dev/null || true
	@echo "Development environment ready!"
	@echo "Edit theknot_scraper/.env to configure settings"

# Quick test
quick-test: validate test
	@echo "All checks passed!"
