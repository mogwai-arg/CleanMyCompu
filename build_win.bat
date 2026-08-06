@echo off
REM Construye CleanMyCompu.exe en Windows.
REM Requisitos: Python 3.10+ y este directorio con el codigo.
REM
REM Uso: doble clic o desde cmd/powershell:
REM   build_win.bat

setlocal
cd /d "%~dp0"

if not exist .venv (
    echo Creando entorno virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: no se encontro Python. Instalalo desde https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

echo Instalando dependencias...
call .venv\Scripts\pip.exe install --quiet --upgrade pip
call .venv\Scripts\pip.exe install --quiet PySide6 send2trash psutil pyinstaller

if not exist assets\AppIcon.ico (
    echo Generando icono...
    call .venv\Scripts\python.exe -c "from PySide6.QtWidgets import QApplication; import sys; app = QApplication(sys.argv); from icons import make_logo_pixmap; pm = make_logo_pixmap(size=256, bg='#1D1D1F', fg='#FFFFFF', radius_ratio=0.225, padding_ratio=0.09); pm.setDevicePixelRatio(1.0); pm.save('assets/AppIcon.ico', 'ICO')"
)

echo Construyendo CleanMyCompu.exe...
call .venv\Scripts\pyinstaller.exe ^
  --windowed ^
  --name CleanMyCompu ^
  --icon assets\AppIcon.ico ^
  --add-data "assets;assets" ^
  --clean --noconfirm ^
  main.py

echo.
echo Listo: dist\CleanMyCompu\CleanMyCompu.exe
echo.
echo La primera vez que la corras, Windows Defender puede mostrar
echo   "Windows protegio tu PC" — tocar "Mas informacion" y "Ejecutar de todos modos".
pause
