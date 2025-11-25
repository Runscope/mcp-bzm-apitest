.PHONY: help install test test-fast test-unit test-integration test-coverage test-watch clean lint format

help:
	@echo "MCP BlazeMeter API Test - Development Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make install          - Install package with test dependencies"
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
	pip install -e ".[test]"

test:
	pytest -v --cov=src --cov-report=term --cov-report=html

test-fast:
	pytest -v -x

test-unit:
	pytest -v -m "not integration"

test-integration:
	pytest -v -m integration tests/test_integration.py

test-coverage:
	pytest --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo ""
	@echo "Coverage report generated in htmlcov/index.html"

test-watch:
	@command -v pytest-watch >/dev/null 2>&1 || { echo "pytest-watch not installed. Run: pip install pytest-watch"; exit 1; }
	pytest-watch

lint:
	flake8 src --max-line-length=108
	black --check src
	isort --check-only src

format:
	black src
	isort src

clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Cleaned up test artifacts"

