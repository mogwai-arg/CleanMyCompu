@echo off
REM Construye CleanMyCompu.exe en Windows.
REM Requisitos: Python 3.10+ y este directorio con el codigo.

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
REM Flags importantes para evitar "Failed to import encodings module":
REM   --collect-all encodings    empaquetar toda la stdlib de encodings
REM   --collect-submodules PySide6  incluir todos los submódulos de Qt
REM   --collect-submodules psutil   idem psutil (tiene binarios nativos)
REM   --hidden-import              módulos importados por string
call .venv\Scripts\pyinstaller.exe ^
  --windowed ^
  --name CleanMyCompu ^
  --icon assets\AppIcon.ico ^
  --add-data "assets;assets" ^
  --collect-all encodings ^
  --collect-submodules PySide6 ^
  --collect-submodules psutil ^
  --hidden-import PySide6.QtSvg ^
  --hidden-import psutil._psutil_windows ^
  --clean --noconfirm ^
  main.py

if errorlevel 1 (
    echo.
    echo ERROR: el build fallo. Ver mensaje arriba.
    pause
    exit /b 1
)

echo.
echo Listo: dist\CleanMyCompu\CleanMyCompu.exe
echo.
echo Para correrlo, doble clic en dist\CleanMyCompu\CleanMyCompu.exe
echo O desde PowerShell: dist\CleanMyCompu\CleanMyCompu.exe
echo.
echo Si el .exe da error de "Failed to import encodings", corre este .bat
echo de nuevo (a veces necesita 2 intentos para bundlear todo).
echo.
echo NOTA: mientras testeas, es MAS RAPIDO correr desde el codigo directo:
echo    .venv\Scripts\python.exe main.py
echo Reservate el .exe para cuando quieras distribuir.
pause
