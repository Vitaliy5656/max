@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

:: Gemini API Configuration (Cloud AI)
set GEMINI_API_KEY=AIzaSyDyLeouOEWajJw-XNQQq5EAm42CNir0ruo
set GEMINI_MODEL=gemini-2.5-flash

:start
echo ===================================================
echo    MAX AI Assistant - Auto Launch
echo ===================================================
echo.

cd /d "%~dp0"

:: Kill old processes strictly by window title first (cleanest)
taskkill /F /FI "WINDOWTITLE eq MAX-API*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq MAX-UI*" /T 2>nul
:: Then by ports assurance
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul
:: Just in case, kill stray node processes (often hang)
taskkill /F /IM node.exe 2>nul
timeout /t 2 /nobreak > nul

if not exist ".venv" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup first.
    pause
    exit /b 1
)

:: Build frontend to ensure latest changes are included
echo Building frontend...
cd frontend
call cmd /c "npm run build 2>&1"
if errorlevel 1 (
    echo [WARNING] Frontend build failed, continuing with existing build...
) else (
    echo [OK] Frontend built successfully!
)
cd ..
echo.

echo Starting API Server on port 8000...
:: Use cmd /k to keep window open if it crashes, remove /min for visibility
start "MAX-API" cmd /k "call .venv\Scripts\activate && python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload"

echo Starting React Frontend on port 5173...
:: Explicitly use cmd /c for npm to avoid PowerShell policy issues
start "MAX-UI" cmd /k "cd frontend && cmd /c npm run dev"

echo.
echo Waiting for servers to initialize...
timeout /t 8 /nobreak > nul

echo Opening browser...
start http://localhost:5173

echo.
echo ===================================================
echo    MAX AI is running!
echo ===================================================
echo.
echo    API:      http://localhost:8000/api/health
echo    Frontend: http://localhost:5173
echo.
echo    Keep this window open to monitor status.
echo    Press any key to restart services...
echo.

pause
cls
echo Restarting services...
goto start

