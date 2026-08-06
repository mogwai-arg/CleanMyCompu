@echo off
REM CleanMyCompu — build launcher. Delega en PowerShell para mostrar UI linda.
REM Doble clic aca y aparece una ventana con barra de progreso.

setlocal
cd /d "%~dp0"

REM Lanza PowerShell escondiendo la ventana de cmd. -ExecutionPolicy Bypass
REM evita que Windows bloquee el script por politica de seguridad.
powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0build_win.ps1"

REM Si PowerShell falla, mostrar aviso.
if errorlevel 1 (
    echo.
    echo Hubo un problema lanzando la ventana de compilacion.
    echo Corriendo en modo texto como fallback...
    echo.
    powershell.exe -ExecutionPolicy Bypass -File "%~dp0build_win.ps1"
    pause
)
