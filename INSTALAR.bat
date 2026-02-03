@echo off
:: =============================================================================
:: INSTALADOR RAPIDO BENDRIX BI - Smart Agent v2.0
:: =============================================================================
:: USO: Doble clic en este archivo y listo!
:: 
:: Este script:
:: 1. Instala Python si no existe
:: 2. Instala dependencias
:: 3. Configura el agente
:: 4. Crea tarea programada
:: 5. Inicia el agente
::
:: Tiempo estimado: 2-3 minutos
:: =============================================================================

title BENDRIX BI - Instalador Rapido
color 0A

echo.
echo  ============================================================
echo.
echo    BENDRIX BI - Smart Agent v2.0
echo    Instalador Rapido
echo.
echo  ============================================================
echo.

:: Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Este instalador requiere permisos de Administrador
    echo [!] Click derecho -^> Ejecutar como administrador
    echo.
    pause
    exit /b 1
)

:: Get script directory
set AGENT_DIR=%~dp0
cd /d "%AGENT_DIR%"

echo [1/6] Verificando Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Python no encontrado. Instalando...
    
    :: Download Python installer
    echo     Descargando Python 3.11...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
    
    echo     Instalando Python (esto toma 1-2 minutos)...
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
    
    :: Refresh PATH
    set PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts
    
    echo     [OK] Python instalado
) else (
    for /f "tokens=2" %%i in ('python --version') do echo     [OK] Python %%i encontrado
)

echo.
echo [2/6] Instalando dependencias...
pip install --quiet --disable-pip-version-check pyodbc requests schedule pywin32 2>nul
if %errorLevel% neq 0 (
    echo     [!] Algunas dependencias fallaron, continuando...
) else (
    echo     [OK] Dependencias instaladas
)

echo.
echo [3/6] Configurando agente...

:: Check if config exists
if exist "config.json" (
    echo     [OK] config.json ya existe
    goto :skip_config
)

:: Prompt for store ID
set /p STORE_ID="    Ingresa el ID de tienda (ej: molldelrio): "

:: Create config file
(
echo {
echo     "store_id": "%STORE_ID%",
echo     "central_server_url": "https://aldelo-bi-production.up.railway.app/api/ingest",
echo     "extraction_interval_minutes": 30,
echo     "retry_attempts": 5,
echo     "retry_delay_seconds": 30,
echo     "db_path_override": null
echo }
) > config.json

echo     [OK] config.json creado

:skip_config

echo.
echo [4/6] Creando carpeta de logs...
if not exist "logs" mkdir logs
echo     [OK] Carpeta logs creada

echo.
echo [5/6] Configurando inicio automatico...

:: Create scheduled task
schtasks /delete /tn "BendrixBI_SmartAgent" /f >nul 2>&1

schtasks /create /tn "BendrixBI_SmartAgent" /tr "pythonw \"%AGENT_DIR%smart_agent.py\"" /sc onlogon /rl highest /f >nul 2>&1
if %errorLevel% neq 0 (
    :: Try alternative method
    schtasks /create /tn "BendrixBI_SmartAgent" /tr "python \"%AGENT_DIR%smart_agent.py\"" /sc onlogon /f >nul 2>&1
)

echo     [OK] Tarea programada creada (inicia con Windows)

echo.
echo [6/6] Iniciando agente...

:: Kill any existing agent process
taskkill /f /im python.exe /fi "WINDOWTITLE eq Smart Agent*" >nul 2>&1

:: Start agent in background
start "Smart Agent v2.0" /min pythonw "%AGENT_DIR%smart_agent.py"
if %errorLevel% neq 0 (
    start "Smart Agent v2.0" /min python "%AGENT_DIR%smart_agent.py"
)

echo     [OK] Agente iniciado en segundo plano

echo.
echo  ============================================================
echo.
echo    INSTALACION COMPLETADA!
echo.
echo    El agente esta corriendo y sincronizara datos cada 30 min.
echo    Los logs se guardan en: %AGENT_DIR%logs\
echo.
echo    Para verificar que funciona:
echo    - Revisa el dashboard en https://aldelo-bi-production.up.railway.app
echo    - O revisa los logs en la carpeta logs\
echo.
echo  ============================================================
echo.

pause
