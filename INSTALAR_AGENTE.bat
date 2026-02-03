@echo off
:: ============================================================
:: INSTALADOR AUTOMATICO - Agente Aldelo BI
:: Ejecutar como Administrador (clic derecho > Ejecutar como admin)
:: ============================================================

echo.
echo ============================================================
echo   INSTALADOR DE AGENTE ALDELO BI
echo   Este script configura el agente para iniciar automaticamente
echo ============================================================
echo.

:: Obtener la ruta actual donde esta este script
set AGENT_DIR=%~dp0
set AGENT_DIR=%AGENT_DIR:~0,-1%

echo Directorio del agente: %AGENT_DIR%
echo.

:: Verificar que existe agent.py
if not exist "%AGENT_DIR%\agent.py" (
    echo ERROR: No se encontro agent.py en esta carpeta.
    echo Asegurese de ejecutar este script desde la carpeta del agente.
    pause
    exit /b 1
)

:: Verificar que existe config.json
if not exist "%AGENT_DIR%\config.json" (
    echo ERROR: No se encontro config.json en esta carpeta.
    pause
    exit /b 1
)

:: Leer el store_id del config.json para nombrar la tarea
for /f "tokens=2 delims=:," %%a in ('findstr "store_id" "%AGENT_DIR%\config.json"') do set STORE_ID=%%~a
set STORE_ID=%STORE_ID: =%
set STORE_ID=%STORE_ID:"=%

echo Store ID detectado: %STORE_ID%
echo.

:: Nombre de la tarea programada
set TASK_NAME=AldeloAgent_%STORE_ID%

:: Eliminar tarea existente si existe
echo Eliminando tarea anterior si existe...
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: Crear la tarea programada
echo Creando tarea programada: %TASK_NAME%
echo.

schtasks /create /tn "%TASK_NAME%" /tr "pythonw \"%AGENT_DIR%\agent.py\"" /sc onlogon /rl highest /f

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo   INSTALACION EXITOSA!
    echo ============================================================
    echo.
    echo El agente "%STORE_ID%" se iniciara automaticamente
    echo cada vez que alguien inicie sesion en Windows.
    echo.
    echo Para verificar, abra el Programador de Tareas y busque:
    echo   %TASK_NAME%
    echo.
    echo Iniciando el agente ahora...
    start "" pythonw "%AGENT_DIR%\agent.py"
    echo.
    echo El agente esta corriendo en segundo plano.
    echo.
) else (
    echo.
    echo ERROR: No se pudo crear la tarea programada.
    echo Asegurese de ejecutar este script como Administrador.
    echo.
)

pause
