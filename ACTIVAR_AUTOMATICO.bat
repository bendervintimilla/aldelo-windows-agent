@echo off
:: ============================================================================
:: ALDELO BI - Auto-Start Configuration
:: Creates a Windows Scheduled Task to run extraction every hour
:: Fixed version: Uses full Python path and working directory
:: ============================================================================

cd /d "%~dp0"

echo.
echo ========================================================================
echo      ALDELO BI - CONFIGURACION AUTOMATICA (v2.0)
echo ========================================================================
echo.
echo Este script creara una tarea programada que extrae datos cada hora.
echo La extraccion continuara incluso si reinicias la computadora.
echo.

:: Get the current directory
set SCRIPT_DIR=%~dp0
set AGENT_PATH=%~dp0agent.py

:: Find Python path
for /f "delims=" %%i in ('where python 2^>nul') do (
    set PYTHON_PATH=%%i
    goto :found_python
)

echo [ERROR] Python no encontrado en el PATH.
echo         Por favor instala Python y asegurate que este en el PATH.
pause
exit /b 1

:found_python
echo.
echo Configuracion detectada:
echo   Python: %PYTHON_PATH%
echo   Script: %AGENT_PATH%
echo   Directorio: %SCRIPT_DIR%
echo.

:: Check for admin rights
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Este script requiere permisos de Administrador.
    echo         Haz clic derecho y selecciona "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

:: Delete existing task if present
echo [*] Eliminando tarea anterior si existe...
schtasks /delete /tn "Aldelo BI Data Extraction" /f >nul 2>&1

:: Create scheduled task using schtasks with full paths
echo [*] Creando tarea programada...

:: Build the command with full paths
set TASK_CMD=cmd /c cd /d "%SCRIPT_DIR%" ^&^& "%PYTHON_PATH%" agent.py

schtasks /Create /TN "Aldelo BI Data Extraction" /TR "%TASK_CMD%" /SC HOURLY /MO 1 /ST 00:00 /RU %USERNAME% /F

if errorlevel 1 (
    echo [ERROR] No se pudo crear la tarea programada.
    echo         Intenta ejecutar como Administrador.
    pause
    exit /b 1
)

:: Run the task immediately as a test
echo.
echo [*] Ejecutando extraccion inicial...
schtasks /Run /TN "Aldelo BI Data Extraction"

echo.
echo ========================================================================
echo [OK] Tarea programada creada exitosamente!
echo.
echo Configuracion:
echo   - Python: %PYTHON_PATH%
echo   - Directorio: %SCRIPT_DIR%
echo   - Frecuencia: Cada hora
echo   - Usuario: %USERNAME%
echo.
echo La extraccion se ejecutara automaticamente cada hora.
echo.
echo Para verificar: Panel de Control ^> Herramientas administrativas ^> 
echo                 Programador de tareas ^> "Aldelo BI Data Extraction"
echo.
echo Para desactivar: Ejecuta DESACTIVAR_AUTOMATICO.bat
echo ========================================================================
echo.

pause
