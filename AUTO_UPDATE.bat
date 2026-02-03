@echo off
REM ============================================
REM AUTO-UPDATE SCRIPT FOR ALDELO BI AGENT
REM Ejecutar cada hora via Task Scheduler
REM ============================================

echo [%date% %time%] Checking for updates... >> "%~dp0update_log.txt"

cd /d "%~dp0"

REM Check if git is available
where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [%date% %time%] ERROR: Git not found >> "%~dp0update_log.txt"
    exit /b 1
)

REM Fetch changes from remote
git fetch origin main 2>> "%~dp0update_log.txt"

REM Check if there are updates
git diff HEAD origin/main --quiet
if %ERRORLEVEL% neq 0 (
    echo [%date% %time%] Updates found, pulling... >> "%~dp0update_log.txt"
    git reset --hard origin/main >> "%~dp0update_log.txt" 2>&1
    
    REM Restart the agent service if running
    net stop "AldeloBIAgent" 2>nul
    timeout /t 3 /nobreak >nul
    net start "AldeloBIAgent" 2>nul
    
    echo [%date% %time%] Update completed and service restarted >> "%~dp0update_log.txt"
) else (
    echo [%date% %time%] No updates available >> "%~dp0update_log.txt"
)
