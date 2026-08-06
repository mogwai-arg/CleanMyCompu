@echo off
REM CleanMyCompu — arma el installer .exe con Inno Setup 6.
REM Delega en PowerShell para mostrar UI linda.

setlocal
cd /d "%~dp0"

REM Chequeo previo: que exista el .exe compilado
if not exist "dist\CleanMyCompu\CleanMyCompu.exe" (
    echo.
    echo ERROR: no encuentro dist\CleanMyCompu\CleanMyCompu.exe
    echo Primero corre build_win.bat para compilar la app.
    echo.
    pause
    exit /b 1
)

powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0build_installer.ps1"

if errorlevel 1 (
    echo.
    echo Hubo un problema. Corriendo en modo texto como fallback...
    powershell.exe -ExecutionPolicy Bypass -File "%~dp0build_installer.ps1"
    pause
)
