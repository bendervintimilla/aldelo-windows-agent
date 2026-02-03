@echo off
REM Installation script for Aldelo Data Extraction Service
REM Run this with Administrator privileges

echo ====================================
echo Aldelo Data Extraction Service
echo Installation Script
echo ====================================
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Ensure we are in the script's directory
cd /d "%~dp0"

echo Ensuring config.json exists...
if not exist "config.json" (
    echo ERROR: config.json not found!
    echo Please make sure you have configured the agent before installing.
    pause
    exit /b 1
)

echo.
echo Installing service...
python service.py install

REM Note: pywin32 may return non-zero on "Service updated"
if %errorLevel% neq 0 (
    echo.
    echo NOTE: If you saw "Service updated", the installation was successful.
    echo Proceeding to start the service...
)

echo.
echo Starting service...
python service.py start

if %errorLevel% neq 0 (
    echo.
    echo ERROR: Service start failed
    echo Check service.log for details
    pause
    exit /b 1
)

echo.
echo ====================================
echo SUCCESS!
echo ====================================
echo.
echo Service installed and started.
echo.
echo To check status:
echo   sc query AldeloDataAgent
echo.
echo To view logs:
echo   type service.log
echo.
pause
