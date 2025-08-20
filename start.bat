@echo off
REM Proxy Browser V2 Startup Script for Windows

echo ========================================================
echo.
echo            Proxy Browser V2 Launcher
echo.
echo ========================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed. Please install Python 3.8+
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if requirements are installed
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
    
    echo Installing Playwright browsers...
    playwright install chromium
)

REM Check if .env file exists
if not exist ".env" (
    echo Warning: No .env file found. Creating from template...
    copy env.example .env
    echo Please edit .env file with your proxy credentials
    echo.
    pause
)

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Create static directory if it doesn't exist
if not exist "app\static" mkdir app\static

REM Start the application
echo.
echo Starting Proxy Browser V2...
echo Open http://localhost:8000 in your browser
echo.
echo Press Ctrl+C to stop the server
echo.

python main.py
