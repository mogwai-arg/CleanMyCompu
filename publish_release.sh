#!/bin/bash
# Publica una nueva versión de CleanMyCompu de forma AUTOMÁTICA:
#   1. Lee __version__ de updater.py
#   2. Buildea la .app y el .dmg
#   3. Crea GitHub Release con el .dmg attached
#   4. Actualiza latest.json en el repo (dispara la notif a todos los usuarios)
#
# Requisitos (una única vez):
#   brew install gh
#   gh auth login    ← elegí GitHub.com y tu método preferido (browser recomendado)
#
# Uso:
#   1. Editá updater.py y bumpéalo (ej. __version__ = "1.2.0")
#   2. ./publish_release.sh
#   3. Cuando te pida notas, escribí los cambios (una línea por bullet) y Ctrl+D
#
# Listo. Los usuarios reciben la notif al abrir la app.

set -e
cd "$(dirname "$0")"

REPO="mogwai-arg/CleanMyCompu"

# ---- Sanity checks ----

if ! command -v gh &> /dev/null; then
    echo "❌ gh CLI no está instalado."
    echo "   Instalá con:  brew install gh"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo "❌ gh no está autenticado."
    echo "   Corré:  gh auth login"
    echo "   Elegí GitHub.com y tu método preferido."
    exit 1
fi

# ---- Detectar versión ----

VERSION=$(grep -E '^__version__' updater.py | sed -E 's/.*"([^"]+)".*/\1/')
if [ -z "$VERSION" ]; then
    echo "❌ No pude detectar __version__ en updater.py"
    exit 1
fi

echo ""
echo "📦  Versión a publicar: v$VERSION"
echo "📁  Repo: $REPO"
echo ""

# Verificar que la release no exista ya
if gh release view "v$VERSION" -R "$REPO" &> /dev/null; then
    echo "⚠️  La release v$VERSION YA EXISTE en GitHub."
    echo "   Editá updater.py y levantá __version__ (ej. a 1.$((${VERSION##*.} + 1)).0)"
    exit 1
fi

# Verificar que el repo NO esté vacío (GitHub requiere al menos 1 commit para crear releases)
if ! gh api "repos/$REPO/commits" --jq '.[0].sha' &> /dev/null; then
    echo "🌱  El repo está vacío. Creando README.md como primer commit…"
    README_B64=$(python3 -c "
import base64
readme = '''# CleanMyCompu

Limpiador de sistema para macOS.

Descargá la última versión desde [Releases](https://github.com/$REPO/releases).
'''
print(base64.b64encode(readme.encode()).decode())
")
    gh api -X PUT "repos/$REPO/contents/README.md" \
        -f message="Initial commit" \
        -f content="$README_B64" > /dev/null
    echo "✅  Repo inicializado."
fi

# ---- Release notes ----

echo "📝  Escribí las release notes (una línea por bullet)."
echo "    Terminá con Ctrl+D:"
echo ""
NOTES=$(cat)
if [ -z "$NOTES" ]; then
    NOTES="Nueva versión $VERSION"
fi

# ---- Build ----

echo ""
echo "🔨  Buildeando .app y .dmg..."
./build_app.sh > /tmp/cleanmycompu_build.log 2>&1 || {
    echo "❌  Falló build_app.sh — ver /tmp/cleanmycompu_build.log"
    tail -20 /tmp/cleanmycompu_build.log
    exit 1
}
./share_app.sh > /tmp/cleanmycompu_share.log 2>&1 || {
    echo "❌  Falló share_app.sh — ver /tmp/cleanmycompu_share.log"
    tail -20 /tmp/cleanmycompu_share.log
    exit 1
}
DMG_SIZE=$(du -h dist/CleanMyCompu.dmg | cut -f1)
echo "✅  dist/CleanMyCompu.dmg listo ($DMG_SIZE)"

# ---- Crear GitHub Release ----

echo ""
echo "🚀  Creando release en GitHub..."
gh release create "v$VERSION" \
    dist/CleanMyCompu.dmg \
    --repo "$REPO" \
    --title "CleanMyCompu v$VERSION" \
    --notes "$NOTES"

DMG_URL="https://github.com/$REPO/releases/download/v$VERSION/CleanMyCompu.dmg"

# ---- Construir latest.json ----

# Usamos Python para el JSON (evita quoting hell del shell)
export CMC_VERSION="$VERSION"
export CMC_URL="$DMG_URL"
export CMC_NOTES="$NOTES"

JSON=$(python3 -c "
import json, os
print(json.dumps({
    'version': os.environ['CMC_VERSION'],
    'url':     os.environ['CMC_URL'],
    'notes':   os.environ['CMC_NOTES'],
}, indent=2, ensure_ascii=False))
")

# ---- Actualizar latest.json via GitHub API ----

echo ""
echo "📝  Actualizando latest.json en el repo (esto dispara la notif)..."

# Obtener SHA del archivo actual si existe
SHA=$(gh api "repos/$REPO/contents/latest.json" --jq '.sha' 2>/dev/null || echo "")

# Encodear en base64 (formato requerido por la Contents API)
CONTENT_B64=$(echo -n "$JSON" | base64)

if [ -n "$SHA" ]; then
    gh api -X PUT "repos/$REPO/contents/latest.json" \
        -f message="Publish v$VERSION" \
        -f content="$CONTENT_B64" \
        -f sha="$SHA" > /dev/null
else
    gh api -X PUT "repos/$REPO/contents/latest.json" \
        -f message="Publish v$VERSION" \
        -f content="$CONTENT_B64" > /dev/null
fi

# ---- Done ----

echo ""
echo "─────────────────────────────────────────────────────────────"
echo "✅  Release v$VERSION publicada."
echo ""
echo "    Release: https://github.com/$REPO/releases/tag/v$VERSION"
echo "    Manifest: https://raw.githubusercontent.com/$REPO/main/latest.json"
echo ""
echo "    Los usuarios recibirán la notificación al abrir la app."
echo "─────────────────────────────────────────────────────────────"
