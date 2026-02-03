@echo off
REM ============================================
REM SETUP AUTO-UPDATE TASK SCHEDULER
REM Run this ONCE as Administrator to enable hourly auto-updates
REM ============================================

echo =========================================
echo   CONFIGURANDO AUTO-UPDATE PARA AGENTE
echo =========================================

REM Get the directory where this script is located
set "AGENT_DIR=%~dp0"
set "UPDATE_SCRIPT=%AGENT_DIR%AUTO_UPDATE.bat"

REM Create scheduled task to run every hour
schtasks /create /tn "AldeloBIAgentAutoUpdate" /tr "\"%UPDATE_SCRIPT%\"" /sc hourly /ru SYSTEM /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo   AUTO-UPDATE CONFIGURADO EXITOSAMENTE
    echo ========================================
    echo.
    echo El agente se actualizara automaticamente cada hora.
    echo Los logs se guardaran en: %AGENT_DIR%update_log.txt
    echo.
    echo Para desactivar: schtasks /delete /tn "AldeloBIAgentAutoUpdate" /f
) else (
    echo.
    echo ERROR: No se pudo crear la tarea programada.
    echo Ejecute este script como Administrador.
)

pause
