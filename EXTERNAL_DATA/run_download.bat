@echo off
chcp 65001 > nul
echo 🚀 Launching Dataset Downloader via Virtual Environment...

if not exist ".venv" (
    echo [ERROR] .venv not found! Please ensure virtual environment is set up.
    pause
    exit /b 1
)

call .venv\Scripts\activate
python scripts\download_datasets.py
pause
