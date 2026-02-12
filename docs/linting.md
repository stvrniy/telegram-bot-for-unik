# Linting and Code Quality Guide

This document describes the linting setup, static type checking, and code quality tools used in this project.

## Overview

This project uses a comprehensive set of tools to maintain code quality:

- **Ruff** - Fast Python linter (written in Rust)
- **mypy** - Static type checker for Python

## Chosen Linter: Ruff

### Why Ruff?

We chose **Ruff** as the primary linter for this project because:

1. **Performance** - Written in Rust, Ruff is 10-100x faster than traditional Python linters
2. **Compatibility** - Supports all pycodestyle (E/F), Pyflakes, and isort rules
3. **Modern Features** - Built-in support for common patterns and auto-fixes
4. **Easy Configuration** - All settings in `pyproject.toml`
5. **Active Development** - Regularly updated with new rules and improvements

### Alternative Linters Considered

- **Flake8** - Popular but slower; Ruff is a drop-in replacement
- **Pylint** - Very comprehensive but slow and verbose
- **Bandit** - Security-focused, can be added later if needed

## Configuration

The linter is configured in `pyproject.toml`:

```toml
[lint]
# Enable rules
select = ["E", "F", "I", "W", "N", "YTT", "ASYNC", "C4", "T20", "RUF", "UP", "B", "A", "COM", "DTZ", "FBT", "PL", "PIE", "TID"]

# Ignore specific rules
ignore = [
    "E501",  # Line too long (handled by formatter)
    "PLR0913",  # Too many arguments
    "PLR0912",  # Too many branches
    "PLR0915",  # Too many statements
    "PLR2004",  # Magic value comparison
    "PLW0603",  # Global statement
    "N802",  # Function name should be lowercase
    "N803",  # Argument name should be lowercase
]

line-length = 100
target-version = "py312"
```

### Rule Categories

- **E/W** - pycodestyle errors/warnings (style)
- **F** - Pyflakes (code errors)
- **I** - isort (import sorting)
- **N** - pep8-naming
- **B** - flake8-bugbear
- **C4** - flake8-comprehensions
- **T20** - flake8-print
- **RUF** - Ruff-specific rules
- **UP** - pyupgrade
- **PL** - Pylint compatibility
- **PIE** - flake8-pie

## Running the Linter

### Check Code

```bash
# Check all Python files
ruff check .

# Check specific file
ruff check handlers/student_commands.py

# Check with statistics
ruff check . --statistics
```

### Auto-fix Issues

```bash
# Auto-fix fixable issues
ruff check . --fix

# Show available fixes
ruff check . --show-fixes
```

## Static Type Checking: mypy

### Why mypy?

mypy is the most popular static type checker for Python. It helps catch type-related bugs before runtime.

### Configuration

Create `mypy.ini` or configure in `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
```

### Running mypy

```bash
# Check all files
mypy .

# Check specific file
mypy handlers/student_commands.py

# Strict mode
mypy --strict .
```

## Pre-commit Hooks

### Setting Up Pre-commit

1. Install pre-commit:
```bash
pip install pre-commit
```

2. Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

3. Install hooks:
```bash
pre-commit install
```

### Running Manually

```bash
# Run on all files
pre-commit run --all-files

# Run on staged files
pre-commit run
```

## CI/CD Integration

### GitHub Actions

Add to `.github/workflows/ci.yml`:

```yaml
name: CI

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff mypy
      
      - name: Run Ruff
        run: |
          ruff check .
          ruff format --check .
      
      - name: Run mypy
        run: mypy .
```

## Build Process Integration

### Makefile

Add to `Makefile`:

```makefile
.PHONY: lint lint-fix typecheck

lint:
	ruff check .

lint-fix:
	ruff check . --fix
	ruff format .

typecheck:
	mypy .

check: lint typecheck
	@echo "All checks passed!"

install-pre-commit:
	pre-commit install
```

### Running Checks

```bash
# Run all checks
make check

# Auto-fix linting issues
make lint-fix

# Type checking
make typecheck

# Install pre-commit hooks
make install-pre-commit
```

## Linting Report

### Initial Results

| Metric | Before | After |
|--------|--------|-------|
| Total Errors | 68 | 0 |
| F401 (unused imports) | 51 | 0 |
| F811 (redefined while unused) | 9 | 0 |
| F841 (unused variables) | 6 | 0 |
| E722 (bare except) | 1 | 0 |
| F541 (f-string without placeholders) | 1 | 0 |

### Issues Fixed

1. **Removed 51 unused imports** across configuration, database, handlers, services, and utils modules
2. **Removed 9 duplicate function definitions** in `handlers/student_commands.py`
3. **Removed 6 unused variables** in various handlers and services
4. **Replaced bare `except`** with `except Exception` in `handlers/cabinet.py`
5. **Fixed f-string without placeholders** in `utils/decorators.py`

### Percentage Fixed Calculation

The 90% target was determined by:
- Initial count: 68 errors
- Fixed count: 68 errors
- Result: 100% (exceeds 90% requirement)

## Best Practices

1. **Run linter before committing** - Use pre-commit hooks
2. **Fix issues promptly** - Don't let lint errors accumulate
3. **Use type hints** - Improves code clarity and mypy effectiveness
4. **Ignore strategically** - Use `# noqa` comments sparingly
5. **Update rules periodically** - Keep ruff and mypy versions current

## Troubleshooting

### Common Issues

1. **False positives**: Add to `ignore` list in `pyproject.toml`
2. **Slow checks**: Ensure using latest ruff version
3. **Type errors**: Add type annotations or `# type: ignore` comments

### Getting Help

- Ruff docs: https://docs.astral.sh/ruff/
- mypy docs: https://mypy.readthedocs.io/
- Pre-commit docs: https://pre-commit.com/
