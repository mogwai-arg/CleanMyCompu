#!/bin/bash
# Reconstruye CleanMyCompu.app desde el código Python.
set -e

cd "$(dirname "$0")"

# Asegurar que las deps de runtime esten instaladas antes de empaquetar
echo "📦 Verificando dependencias runtime..."
./.venv/bin/pip install --quiet \
  PySide6 send2trash psutil pyinstaller imagehash Pillow requests

echo "🔨 Construyendo CleanMyCompu.app..."
./.venv/bin/pyinstaller \
  --windowed \
  --name CleanMyCompu \
  --osx-bundle-identifier com.cleanmycompu.app \
  --icon assets/AppIcon.icns \
  --add-data "assets:assets" \
  --collect-submodules PySide6 \
  --collect-submodules psutil \
  --collect-submodules PIL \
  --collect-submodules imagehash \
  --hidden-import PIL.Image \
  --hidden-import PIL._imaging \
  --hidden-import imagehash \
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
