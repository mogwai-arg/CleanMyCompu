#!/bin/bash
# Empaca dist/CleanMyCompu.app en un .dmg listo para compartir.
# Uso: ./share_app.sh   (si la .app no existe, corre ./build_app.sh primero)
set -e
cd "$(dirname "$0")"

if [ ! -d "dist/CleanMyCompu.app" ]; then
  echo "🔨 dist/CleanMyCompu.app no existe — construyendo primero..."
  ./build_app.sh
fi

echo "📦 Preparando staging para el .dmg..."
STAGING=/tmp/cleanmycompu_dmg
rm -rf "$STAGING"
mkdir -p "$STAGING"

# 1) Copiar la app
cp -R "dist/CleanMyCompu.app" "$STAGING/"

# 2) Symlink a /Applications (el clásico "drag here")
ln -s /Applications "$STAGING/Applications"

# 3) Instrucciones legibles
cp LEEME.txt "$STAGING/LEEME.txt"

# 4) Instalador de 1 clic que también quita quarantine (evita el bug de
#    "app dañada" con apps no firmadas por Apple)
cat > "$STAGING/Instalar.command" << 'EOF'
#!/bin/bash
# Instala CleanMyCompu en /Applications y quita la marca de quarantine
# que macOS pone al descargar el .dmg, evitando el error "app dañada".

set -e
DMG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$DMG_DIR/CleanMyCompu.app"
DST="/Applications/CleanMyCompu.app"

echo ""
echo "══════════════════════════════════════════════════"
echo "  Instalando CleanMyCompu…"
echo "══════════════════════════════════════════════════"
echo ""

if [ ! -d "$SRC" ]; then
  echo "❌ No encontré CleanMyCompu.app en el .dmg."
  echo "   Asegurate de correr esto desde el .dmg montado."
  read -n 1 -s -r -p "Presioná una tecla para cerrar…"
  exit 1
fi

echo "→ Copiando a /Applications…"
rm -rf "$DST"
cp -R "$SRC" "$DST"

echo "→ Quitando marca de descargado (com.apple.quarantine)…"
xattr -cr "$DST"

echo "→ Re-firmando localmente…"
codesign -s - --force --deep "$DST" 2>/dev/null || true

echo ""
echo "✅ CleanMyCompu instalada correctamente."
echo ""
echo "   Abriendo la app…"
sleep 1
open "$DST"

echo ""
echo "   Podés cerrar esta ventana."
sleep 3
EOF
chmod +x "$STAGING/Instalar.command"

echo "💿 Creando .dmg..."
rm -f dist/CleanMyCompu.dmg
hdiutil create \
  -volname "CleanMyCompu" \
  -srcfolder "$STAGING" \
  -ov -format UDZO \
  -fs HFS+ \
  dist/CleanMyCompu.dmg > /dev/null

rm -rf "$STAGING"

SIZE=$(du -h dist/CleanMyCompu.dmg | cut -f1)
echo ""
echo "✅ Listo: dist/CleanMyCompu.dmg  ($SIZE)"
echo ""
echo "   Compartilo por WeTransfer, Google Drive, AirDrop, etc."
echo "   Tu amigo abre el .dmg → arrastra CleanMyCompu al ícono 'Applications'."
echo "   La primera vez tiene que hacer clic derecho → 'Abrir' (ver LEEME.txt)"
