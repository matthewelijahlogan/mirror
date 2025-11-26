@echo off
setlocal enabledelayedexpansion

echo ================================================
echo       MIRROR, MIRROR — STARTUP SCRIPT
echo ================================================
echo.

:: ---------------- 1) Check Python ----------------
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python not found. Install Python 3.10+ and ensure it's on PATH.
    pause
    exit /b
)

:: ---------------- 2) Ensure virtualenv ----------------
python -m virtualenv --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing virtualenv...
    python -m pip install --upgrade pip
    python -m pip install virtualenv
)

:: ---------------- 3) Create virtual environment ----------------
if not exist venv (
    echo Creating virtual environment...
    python -m virtualenv venv
) else (
    echo Using existing virtual environment.
)

:: ---------------- 4) Activate venv ----------------
call venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo Failed to activate virtual environment. Exiting.
    pause
    exit /b
)
echo Virtual environment activated.

:: ---------------- 5) Install dependencies ----------------
if exist requirements.txt (
    echo Installing dependencies from requirements.txt...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
) else (
    echo requirements.txt not found. Installing default dependencies...
    python -m pip install --upgrade pip
    python -m pip install fastapi uvicorn jinja2 python-multipart starlette pydantic watchdog
)
echo Dependencies installed.

:: ---------------- 6) Verify main.py ----------------
if not exist main.py (
    echo main.py not found in current directory. Please run this script from project root.
    pause
    exit /b
)

:: ---------------- 7) Launch server ----------------
echo Starting uvicorn server (logs will appear in this window)...
:: Start uvicorn in a separate window to avoid blocking
start "uvicorn" cmd /k "uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

:: ---------------- 8) Wait for server to be ready ----------------
echo Waiting for server to start...
timeout /t 3 >nul

:: ---------------- 9) Open browser ----------------
start "" "http://127.0.0.1:8000/"

echo.
echo ================================================
echo Mirror Mirror should now be running!
echo Press CTRL+C in uvicorn window to stop.
echo ================================================
pause
