@echo off
REM GenesisX Web Application Launcher for Windows

echo Starting GenesisX Web Application...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9 or higher from python.org
    pause
    exit /b 1
)

REM Check if required dependencies are installed
echo Checking dependencies...
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Flask...
    pip install flask flask-cors
)

echo.
echo Launching GenesisX Web UI...
echo The application will be available at http://localhost:5000
echo.
python web\app.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to start GenesisX
    pause
    exit /b 1
)
