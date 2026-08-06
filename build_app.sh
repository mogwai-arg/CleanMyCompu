#!/bin/bash
# Reconstruye CleanMyCompu.app desde el código Python.
set -e

cd "$(dirname "$0")"

echo "🔨 Construyendo CleanMyCompu.app..."
./.venv/bin/pyinstaller \
  --windowed \
  --name CleanMyCompu \
  --osx-bundle-identifier com.cleanmycompu.app \
  --icon assets/AppIcon.icns \
  --add-data "assets:assets" \
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
