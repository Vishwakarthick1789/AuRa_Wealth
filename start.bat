@echo off
setlocal

echo ===================================================
echo Gen Z Wealth Forecaster App - Setup and Execution
echo ===================================================

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Create Virtual Environment
if not exist venv (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Virtual environment already exists.
)

:: Activate Virtual Environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Install Dependencies
echo [INFO] Upgrading pip to avoid building packages from source...
python -m pip install --upgrade pip
echo [INFO] Installing dependencies from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

:: Run Application
echo [INFO] Launching Application...
python app.py
if %errorlevel% neq 0 (
    echo [ERROR] Application crashed or failed to start.
    pause
    exit /b 1
)

pause
