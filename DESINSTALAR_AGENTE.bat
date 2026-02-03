@echo off
:: Desinstala la tarea programada del agente

set AGENT_DIR=%~dp0
for /f "tokens=2 delims=:," %%a in ('findstr "store_id" "%AGENT_DIR%\config.json"') do set STORE_ID=%%~a
set STORE_ID=%STORE_ID: =%
set STORE_ID=%STORE_ID:"=%

set TASK_NAME=AldeloAgent_%STORE_ID%

echo Eliminando tarea: %TASK_NAME%
schtasks /delete /tn "%TASK_NAME%" /f

echo.
echo Tarea eliminada. El agente ya no iniciara automaticamente.
pause
