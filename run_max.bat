@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

echo ===================================================
echo 🚀 Starting MAX AI Assistant...
echo ===================================================
echo.

if not exist ".venv" (
    echo [ERROR] Virtual environment not found in .venv!
    echo Please install dependencies first.
    echo.
    pause
    exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Starting application...
python run.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application crashed with exit code %errorlevel%
)

echo.
pause
