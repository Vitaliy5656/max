@echo off
:: Enable UTF-8 encoding for the console
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

:: --- CRITICAL: Set Working Directory to Project Root ---
:: This allows the script to be clicked from "scripts/knowledge_boost/" 
:: but act as if it's running from "MAX/" root.
pushd "%~dp0..\.."

set "PYTHON_EXE=C:\Program Files\Siril\python\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found at: %PYTHON_EXE%
    pause
    exit /b 1
)

echo [MAX] Using portable Python (Siril)...
"%PYTHON_EXE%" --version
echo.

echo [MAX] Working Directory: %CD%
echo [MAX] Scripts Location: EXTERNAL_DATA/knowledge_boost/
echo.

echo [MAX] Starting Import (LITE TEST)...
"%PYTHON_EXE%" EXTERNAL_DATA/knowledge_boost/import_boost.py

echo.
echo [MAX] Verifying Database...
"%PYTHON_EXE%" EXTERNAL_DATA/knowledge_boost/check_db.py

echo.
echo [DONE] Execution complete.
popd
pause
