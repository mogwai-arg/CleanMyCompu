#!/bin/bash
# Reconstruye CleanMyCompu.app desde el código Python.
set -e

cd "$(dirname "$0")"

# Asegurar que las deps de runtime esten instaladas antes de empaquetar
echo "📦 Verificando dependencias runtime..."
./.venv/bin/pip install --quiet \
  PySide6 send2trash psutil pyinstaller imagehash Pillow requests

echo "🔨 Construyendo CleanMyCompu.app..."
# OJO: nada de --collect-submodules PIL/imagehash — arrastra scipy entero
# (100+ MB) y todos los plugins de PIL (50+ formatos). Solo hidden-imports
# específicos para las clases que realmente usamos.
./.venv/bin/pyinstaller \
  --windowed \
  --name CleanMyCompu \
  --osx-bundle-identifier com.cleanmycompu.app \
  --icon assets/AppIcon.icns \
  --add-data "assets:assets" \
  --hidden-import PIL.Image \
  --hidden-import PIL.JpegImagePlugin \
  --hidden-import PIL.PngImagePlugin \
  --hidden-import PIL.BmpImagePlugin \
  --hidden-import PIL.TiffImagePlugin \
  --hidden-import PIL.WebPImagePlugin \
  --hidden-import PIL._imaging \
  --hidden-import imagehash \
  --hidden-import numpy \
  --collect-submodules numpy \
  --exclude-module scipy \
  --exclude-module scipy.special \
  --exclude-module matplotlib \
  --exclude-module pytest \
  --exclude-module notebook \
  --exclude-module tests \
  --clean --noconfirm \
  main.py > /tmp/cleanmycompu-build.log 2>&1

echo "🧹 Limpiando xattr..."
xattr -cr dist/CleanMyCompu.app

echo "✍️  Firmando (ad-hoc)..."
codesign -s - --force --deep dist/CleanMyCompu.app 2>/dev/null || true

SIZE=$(du -sh dist/CleanMyCompu.app | cut -f1)
echo ""
echo "✅ Listo: dist/CleanMyCompu.app  ($SIZE)"
echo ""
echo "   Para instalarla:"
echo "     cp -r dist/CleanMyCompu.app /Applications/"
