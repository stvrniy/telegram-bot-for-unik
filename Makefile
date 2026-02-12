# Makefile for Telegram Education Bot
# Contains all commands for development, testing, and code quality

.PHONY: help install install-dev lint lint-fix typecheck check test clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make install        - Install production dependencies"
	@echo "  make install-dev    - Install development dependencies"
	@echo "  make lint           - Run ruff linter"
	@echo "  make lint-fix       - Auto-fix linting issues"
	@echo "  make typecheck      - Run mypy type checker"
	@echo "  make check          - Run all code checks (lint + typecheck)"
	@echo "  make test           - Run tests"
	@echo "  make clean          - Clean up cache and build files"

# Install dependencies
install:
	pip install -r requirements.txt

# Install development dependencies
install-dev:
	pip install -r requirements.txt -r requirements-test.txt
	pip install ruff mypy pre-commit

# Run ruff linter
lint:
	ruff check .

# Auto-fix linting issues
lint-fix:
	ruff check . --fix
	ruff format .

# Run mypy type checker
typecheck:
	mypy . --ignore-missing-imports

# Run all code checks
check: lint typecheck
	@echo "✓ All code checks passed!"

# Run tests
test:
	python -m pytest tests/ -v

# Clean up
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .ruff_cache 2>/dev/null || true
	rm -rf .coverage 2>/dev/null || true
	rm -rf htmlcov 2>/dev/null || true

# Install pre-commit hooks
install-pre-commit:
	pre-commit install

# Run pre-commit on all files
run-pre-commit:
	pre-commit run --all-files

# Docker commands
docker-build:
	docker build -t telegram-edu-bot .

docker-run:
	docker run -it --rm -p 8080:8080 telegram-edu-bot

# Code coverage report
coverage:
	python -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"
