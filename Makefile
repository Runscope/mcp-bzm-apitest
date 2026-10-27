.PHONY: help install test test-fast test-unit test-integration test-coverage test-watch clean lint format

# Tool resolution: prefer the repo's .venv (created by `make install` via uv);
# fall back to PATH so CI and already-activated environments keep working.
# Bare `pytest` broke on cold hosts (host python 3.9 vs requires-python >=3.11).
PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
PYTEST := $(PYTHON) -m pytest

help:
	@echo "MCP BlazeMeter API Test - Development Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make install          - Create .venv and install package with test dependencies (uv)"
	@echo "  make test             - Run all tests with coverage"
	@echo "  make test-fast        - Run tests quickly (stop on first failure)"
	@echo "  make test-unit        - Run only unit tests"
	@echo "  make test-integration - Run only integration tests"
	@echo "  make test-coverage    - Generate detailed coverage report"
	@echo "  make test-watch       - Run tests in watch mode"
	@echo "  make lint             - Run linting checks"
	@echo "  make format           - Format code with black and isort"
	@echo "  make clean            - Clean up test artifacts"

install:
	@command -v uv >/dev/null 2>&1 || { echo "uv not installed. Install from https://docs.astral.sh/uv/ then re-run, or manually: python3.11 -m venv .venv && .venv/bin/pip install -e '.[test]'"; exit 1; }
	uv sync --extra test

test:
	$(PYTEST) -v --cov=src --cov-report=term --cov-report=html

test-fast:
	$(PYTEST) -v -x

test-unit:
	$(PYTEST) -v -m "not integration"

test-integration:
	$(PYTEST) -v -m integration tests/test_integration.py

test-coverage:
	$(PYTEST) --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo ""
	@echo "Coverage report generated in htmlcov/index.html"

test-watch:
	@command -v pytest-watch >/dev/null 2>&1 || { echo "pytest-watch not installed. Run: pip install pytest-watch"; exit 1; }
	pytest-watch

lint:
	$(PYTHON) -m flake8 src --max-line-length=108
	$(PYTHON) -m black --check src --target-version py311
	$(PYTHON) -m isort --check-only src

format:
	$(PYTHON) -m black src --target-version py311
	$(PYTHON) -m isort src

clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Cleaned up test artifacts"

