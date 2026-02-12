@echo off
REM Telegram Bot - Development Launch Script (Windows)

setlocal

REM Configuration
set BOT_DIR=%~dp0..\..
set VENV_DIR=%BOT_DIR%\venv
set DATA_DIR=%BOT_DIR%\data
set LOG_DIR=%BOT_DIR%\logs

echo ============================================
echo Telegram Educational Bot - Development Mode
echo ============================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.11+ and add it to PATH
    exit /b 1
)

REM Create directories if not exist
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Check virtual environment
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        exit /b 1
    )
    echo Installing dependencies...
    "%VENV_DIR%\Scripts\pip.exe" install --upgrade pip
    "%VENV_DIR%\Scripts\pip.exe" install -r "%BOT_DIR%\requirements.txt"
)

REM Check .env file
if not exist "%BOT_DIR%\.env" (
    echo WARNING: .env file not found!
    echo Creating from .env.example...
    if exist "%BOT_DIR%\.env.example" (
        copy "%BOT_DIR%\.env.example" "%BOT_DIR%\.env"
        echo Please edit .env and add your BOT_TOKEN
    ) else (
        echo ERROR: .env.example not found!
    )
)

REM Set environment variables
set ENVIRONMENT=development
set LOG_LEVEL=DEBUG

echo.
echo Starting bot...
echo Press Ctrl+C to stop
echo.

REM Activate venv and run
"%VENV_DIR%\Scripts\python.exe" "%BOT_DIR%\main.py"

endlocal
