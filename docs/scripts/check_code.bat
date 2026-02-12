@echo off
REM Comprehensive code check script for Windows
REM This script runs all code quality checks

echo ============================================
echo Telegram Education Bot - Code Quality Check
echo ============================================
echo.

REM Check if ruff is installed
where ruff >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Ruff is not installed. Installing...
    pip install ruff
    echo.
)

REM Run ruff linter
echo [1/2] Running Ruff linter...
echo ------------------------------------------
ruff check .
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Linting issues found. Run 'ruff check . --fix' to auto-fix.
) else (
    echo [OK] No linting issues found.
)
echo.

REM Check if mypy is installed
where mypy >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] mypy is not installed. Skipping type checking.
    echo To install: pip install mypy
) else (
    echo [2/2] Running mypy type checker...
    echo ------------------------------------------
    mypy . --ignore-missing-imports --no-error-summary
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [WARNING] Type checking issues found.
    ) else (
        echo [OK] Type checking passed.
    )
)

echo.
echo ============================================
echo Code quality check completed!
echo ============================================
echo.
echo Quick fixes:
echo   - Auto-fix linting: ruff check . --fix
echo   - Install pre-commit: pip install pre-commit && pre-commit install
echo   - Run pre-commit: pre-commit run --all-files
echo.
pause
