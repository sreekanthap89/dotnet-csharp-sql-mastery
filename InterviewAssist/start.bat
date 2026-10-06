@echo off
REM ==============================================================================
REM Interview Assist - 1-Click Universal Launcher (Windows)
REM ==============================================================================

echo ========================================================
echo   Starting Interview Assist (RAG Interview Platform)
echo ========================================================

cd /d "%~dp0"
set "BACKEND_DIR=%~dp0backend"
set "VENV_DIR=%BACKEND_DIR%\venv"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.9+ from https://www.python.org and check "Add to PATH"
    pause
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [INFO] Creating Python virtual environment...
    python -m venv "%VENV_DIR%"
)

call "%VENV_DIR%\Scripts\activate.bat"

echo [INFO] Checking dependencies...
pip install -q -r "%BACKEND_DIR%\requirements.txt"

echo [INFO] Opening default browser...
start http://localhost:8000

echo [INFO] Launching FastAPI server on http://localhost:8000 ...
cd "%BACKEND_DIR%"
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
