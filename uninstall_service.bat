@echo off
REM Uninstallation script for Aldelo Data Extraction Service
REM Run this with Administrator privileges

echo ====================================
echo Aldelo Data Extraction Service
echo Uninstallation Script
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

echo Stopping service...
python service.py stop

echo.
echo Removing service...
python service.py remove

if %errorLevel% neq 0 (
    echo.
    echo ERROR: Service removal failed
    pause
    exit /b 1
)

echo.
echo ====================================
echo SUCCESS!
echo ====================================
echo Service has been removed.
echo.
pause
