@echo off
:: =============================================================================
:: INSTALADOR MAESTRO BENDRIX BI - Todo en Uno
:: =============================================================================
:: Este script hace TODO:
:: 1. Instala Python (si no existe)
:: 2. Instala Git via winget (si no existe)
:: 3. Clona el repositorio / actualiza código
:: 4. Configura el agente
:: 5. Crea tareas programadas (agente + auto-update)
:: 6. Extrae datos históricos
:: 7. Inicia el agente
::
:: USO: Click derecho -> Ejecutar como administrador
:: =============================================================================

title BENDRIX BI - Instalador Maestro v2.0
color 0A

echo.
echo  ============================================================
echo.
echo    BENDRIX BI - INSTALADOR MAESTRO
echo    Smart Agent v2.0 con Auto-Update
echo.
echo  ============================================================
echo.

:: Check admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Ejecutar como Administrador
    echo         Click derecho -^> Ejecutar como administrador
    pause
    exit /b 1
)

:: Get install directory
set INSTALL_DIR=%~dp0
cd /d "%INSTALL_DIR%"

:: Ask for store info
echo.
set /p STORE_ID="Ingresa el ID de tienda (ej: petit_palace): "
set /p STORE_NAME="Ingresa el nombre (ej: Petit Palace): "
echo.

:: =============================================================================
echo [1/8] Verificando Python...
:: =============================================================================
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo       Python no encontrado. Instalando via winget...
    winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements -h
    if %errorLevel% neq 0 (
        echo       Intentando descarga directa...
        powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
        "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
    )
    :: Refresh PATH
    set PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts
    timeout /t 3 /nobreak >nul
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo       [OK] Python %%i

:: =============================================================================
echo [2/8] Instalando dependencias Python...
:: =============================================================================
pip install --quiet --disable-pip-version-check pyodbc requests schedule pywin32 2>nul
echo       [OK] Dependencias instaladas

:: =============================================================================
echo [3/8] Verificando Git...
:: =============================================================================
git --version >nul 2>&1
if %errorLevel% neq 0 (
    echo       Git no encontrado. Instalando via winget...
    winget install Git.Git --accept-package-agreements --accept-source-agreements -h
    if %errorLevel% neq 0 (
        echo       Descargando Git manualmente...
        bitsadmin /transfer gitdownload /download /priority normal https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe %TEMP%\git_installer.exe
        "%TEMP%\git_installer.exe" /VERYSILENT /NORESTART
    )
    :: Refresh PATH
    set PATH=%PATH%;C:\Program Files\Git\bin;C:\Program Files\Git\cmd
    timeout /t 3 /nobreak >nul
)
for /f "tokens=3" %%i in ('git --version 2^>^&1') do echo       [OK] Git %%i

:: =============================================================================
echo [4/8] Configurando repositorio Git (sin login - repo publico)...
:: =============================================================================
:: Disable credential prompts for public repo
set GIT_TERMINAL_PROMPT=0
git config --global credential.helper ""

if exist ".git" (
    echo       Repositorio existe, actualizando...
    git -c credential.helper= fetch origin main >nul 2>&1
    git checkout origin/main -- windows-agent >nul 2>&1
    copy /y windows-agent\*.py . >nul 2>&1
    copy /y windows-agent\*.bat . >nul 2>&1
    echo       [OK] Codigo actualizado desde GitHub
) else (
    echo       Inicializando repositorio...
    git init >nul 2>&1
    git remote add origin https://github.com/bendervintimilla/aldelo-BI.git 2>nul
    git -c credential.helper= fetch origin main
    git checkout origin/main -- windows-agent
    copy /y windows-agent\*.py . >nul 2>&1
    copy /y windows-agent\*.bat . >nul 2>&1
    echo       [OK] Repositorio clonado
)

:: =============================================================================
echo [5/8] Configurando agente para %STORE_NAME%...
:: =============================================================================
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
if not exist "tools" mkdir tools
if not exist "utils" mkdir utils
xcopy /s /y /q windows-agent\tools\* tools\ >nul 2>&1
xcopy /s /y /q windows-agent\utils\* utils\ >nul 2>&1
echo       [OK] config.json creado para %STORE_NAME%

:: =============================================================================
echo [6/8] Creando tarea de inicio automatico...
:: =============================================================================
schtasks /delete /tn "BendrixBI_%STORE_ID%" /f >nul 2>&1
schtasks /create /tn "BendrixBI_%STORE_ID%" /tr "pythonw \"%INSTALL_DIR%smart_agent.py\"" /sc onlogon /rl highest /f >nul 2>&1
echo       [OK] Agente iniciara con Windows

:: =============================================================================
echo [7/8] Creando tarea de auto-update (cada hora)...
:: =============================================================================
:: Create update script
(
echo @echo off
echo cd /d "%INSTALL_DIR%"
echo git fetch origin main ^>nul 2^>^&1
echo git checkout origin/main -- windows-agent ^>nul 2^>^&1
echo copy /y windows-agent\smart_agent.py . ^>nul 2^>^&1
echo copy /y windows-agent\tools\*.py tools\ ^>nul 2^>^&1
echo copy /y windows-agent\utils\*.py utils\ ^>nul 2^>^&1
echo taskkill /f /fi "WINDOWTITLE eq Smart Agent*" ^>nul 2^>^&1
echo timeout /t 2 /nobreak ^>nul
echo start "Smart Agent - %STORE_NAME%" /min pythonw smart_agent.py
) > auto_update.bat

schtasks /delete /tn "BendrixBI_AutoUpdate_%STORE_ID%" /f >nul 2>&1
schtasks /create /tn "BendrixBI_AutoUpdate_%STORE_ID%" /tr "\"%INSTALL_DIR%auto_update.bat\"" /sc hourly /f >nul 2>&1
echo       [OK] Auto-update programado cada hora

:: =============================================================================
echo [8/8] Iniciando agente...
:: =============================================================================
taskkill /f /fi "WINDOWTITLE eq Smart Agent*" >nul 2>&1
start "Smart Agent - %STORE_NAME%" /min pythonw "%INSTALL_DIR%smart_agent.py"
echo       [OK] Agente iniciado en segundo plano

:: =============================================================================
:: RESUMEN
:: =============================================================================
echo.
echo  ============================================================
echo.
echo    INSTALACION COMPLETADA!
echo.
echo    Store ID:     %STORE_ID%
echo    Store Name:   %STORE_NAME%
echo    Directorio:   %INSTALL_DIR%
echo.
echo    El agente:
echo    [X] Sincroniza datos cada 30 minutos
echo    [X] Se actualiza desde GitHub cada hora
echo    [X] Inicia automaticamente con Windows
echo.
echo    Para actualizar TODOS los locales:
echo    Solo haz "git push" en tu Mac y espera 1 hora
echo.
echo  ============================================================
echo.
echo.
set /p EXTRACT_HIST="Extraer datos historicos ahora? (s/n): "
if /i "%EXTRACT_HIST%"=="s" (
    echo.
    echo Extrayendo datos historicos...
    python extract_historical.py
)
echo.
pause
