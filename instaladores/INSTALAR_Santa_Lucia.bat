@echo off
:: INSTALADOR AUTOMATICO - Santa Lucia
title BENDRIX BI - Santa Lucia
color 0A
set STORE_ID=santa_lucia
set STORE_NAME=Santa Lucia
goto :install

:install
echo.
echo  ============================================================
echo    BENDRIX BI - Smart Agent v2.0
echo    Local: %STORE_NAME%
echo  ============================================================
echo.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Ejecutar como Administrador
    pause
    exit /b 1
)

set AGENT_DIR=%~dp0..\
cd /d "%AGENT_DIR%"

echo [1/5] Verificando Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo     Instalando Python...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
    set PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts
)
echo     [OK] Python listo

echo [2/5] Instalando dependencias...
pip install --quiet --disable-pip-version-check pyodbc requests schedule pywin32 2>nul
echo     [OK] Dependencias listas

echo [3/5] Configurando agente...
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
echo     [OK] Configurado para %STORE_NAME%

echo [4/5] Creando tarea programada...
if not exist "logs" mkdir logs
schtasks /delete /tn "BendrixBI_%STORE_ID%" /f >nul 2>&1
schtasks /create /tn "BendrixBI_%STORE_ID%" /tr "pythonw \"%AGENT_DIR%smart_agent.py\"" /sc onlogon /rl highest /f >nul 2>&1
echo     [OK] Inicio automatico configurado

echo [5/5] Iniciando agente...
start "Smart Agent - %STORE_NAME%" /min pythonw "%AGENT_DIR%smart_agent.py"
echo     [OK] Agente iniciado

echo.
echo  ============================================================
echo    INSTALACION COMPLETADA - %STORE_NAME%
echo    El agente sincronizara datos cada 30 minutos
echo  ============================================================
echo.
pause
