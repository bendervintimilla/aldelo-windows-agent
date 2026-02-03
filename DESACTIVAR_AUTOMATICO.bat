@echo off
:: ============================================================================
:: ALDELO BI - Disable Automatic Extraction
:: ============================================================================

echo.
echo ========================================================================
echo      ALDELO BI - DESACTIVAR EXTRACCION AUTOMATICA
echo ========================================================================
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

schtasks /delete /tn "Aldelo BI Data Extraction" /f

if errorlevel 1 (
    echo [!] No se encontro la tarea programada.
) else (
    echo [OK] Extraccion automatica desactivada.
)

echo.
pause
