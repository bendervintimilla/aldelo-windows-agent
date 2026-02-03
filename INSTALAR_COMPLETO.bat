@echo off
:: =============================================================================
:: INSTALADOR COMPLETO CON AUTO-UPDATE
:: Incluye: Instalacion + Configuracion de Git Pull automatico cada hora
:: =============================================================================

title BENDRIX BI - Instalador Completo
color 0A

echo.
echo  ============================================================
echo    BENDRIX BI - Smart Agent v2.0
echo    INSTALADOR CON AUTO-UPDATE
echo  ============================================================
echo.

:: Check admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Ejecutar como Administrador
    pause
    exit /b 1
)

:: Get current directory (where this bat is located)
set INSTALL_DIR=%~dp0
cd /d "%INSTALL_DIR%"

:: Ask for store ID
set /p STORE_ID="Ingresa el ID de tienda (ej: petit_palace): "
set /p STORE_NAME="Ingresa el nombre visible (ej: Petit Palace): "

echo.
echo [1/7] Verificando Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo     Descargando Python 3.11...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
    echo     Instalando Python (1-2 minutos)...
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
    set PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts
    timeout /t 5 /nobreak >nul
)
echo     [OK] Python listo

echo.
echo [2/7] Instalando dependencias Python...
pip install --quiet --disable-pip-version-check pyodbc requests schedule pywin32 2>nul
echo     [OK] Dependencias listas

echo.
echo [3/7] Verificando Git...
git --version >nul 2>&1
if %errorLevel% neq 0 (
    echo     Git no encontrado. Instalando...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe' -OutFile '%TEMP%\git_installer.exe'"
    "%TEMP%\git_installer.exe" /VERYSILENT /NORESTART
    set PATH=%PATH%;C:\Program Files\Git\bin
    timeout /t 5 /nobreak >nul
)
echo     [OK] Git listo

echo.
echo [4/7] Clonando/Actualizando repositorio...
if exist ".git" (
    echo     Actualizando codigo existente...
    git pull origin main
) else (
    echo     Clonando repositorio...
    cd ..
    rmdir /s /q windows-agent 2>nul
    git clone https://github.com/bendervintimilla/aldelo-BI.git temp_clone
    move temp_clone\windows-agent windows-agent
    rmdir /s /q temp_clone
    cd windows-agent
)
echo     [OK] Codigo actualizado

echo.
echo [5/7] Configurando agente para %STORE_NAME%...
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
if not exist "logs" mkdir logs
echo     [OK] config.json creado

echo.
echo [6/7] Configurando Auto-Update (cada hora)...
:: Create the auto-update script
(
echo @echo off
echo cd /d "%INSTALL_DIR%"
echo git pull origin main ^>nul 2^>^&1
echo :: Restart agent if running
echo taskkill /f /fi "WINDOWTITLE eq Smart Agent*" ^>nul 2^>^&1
echo timeout /t 2 /nobreak ^>nul
echo start "Smart Agent - %STORE_NAME%" /min pythonw smart_agent.py
) > auto_update.bat

:: Schedule hourly auto-update
schtasks /delete /tn "BendrixBI_AutoUpdate_%STORE_ID%" /f >nul 2>&1
schtasks /create /tn "BendrixBI_AutoUpdate_%STORE_ID%" /tr "\"%INSTALL_DIR%auto_update.bat\"" /sc hourly /f >nul 2>&1
echo     [OK] Auto-update programado (cada hora)

echo.
echo [7/7] Configurando inicio automatico e iniciando agente...
schtasks /delete /tn "BendrixBI_%STORE_ID%" /f >nul 2>&1
schtasks /create /tn "BendrixBI_%STORE_ID%" /tr "pythonw \"%INSTALL_DIR%smart_agent.py\"" /sc onlogon /rl highest /f >nul 2>&1

:: Kill existing and start fresh
taskkill /f /fi "WINDOWTITLE eq Smart Agent*" >nul 2>&1
start "Smart Agent - %STORE_NAME%" /min pythonw "%INSTALL_DIR%smart_agent.py"
echo     [OK] Agente iniciado

echo.
echo  ============================================================
echo.
echo    INSTALACION COMPLETADA!
echo.
echo    Store ID:    %STORE_ID%
echo    Store Name:  %STORE_NAME%
echo.
echo    El agente:
echo    - Sincroniza datos cada 30 minutos
echo    - Se actualiza automaticamente cada hora desde GitHub
echo    - Inicia automaticamente con Windows
echo.
echo    Para actualizar TODOS los locales:
echo    Solo haz "git push" y espera 1 hora (o reinicia el PC)
echo.
echo  ============================================================
echo.
pause
