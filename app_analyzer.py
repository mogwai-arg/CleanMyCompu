"""
Análisis inteligente de AppData.

Escanea AppData\\Local y AppData\\Roaming, identifica apps CONOCIDAS y da
recomendaciones específicas de qué carpetas internas se pueden borrar
sin romper la app.

Cada app tiene 3 tipos de contenido:
  - safe: caches, temporales, previews — se regeneran, borrar libre
  - caution: media caches grandes, historial — se regenera pero podés
    perder atajos/rapidez temporalmente
  - dangerous: settings, preferencias, base de datos — SI borrás pierdes
    tu configuración de la app (login, ajustes, historial de proyectos)

Para apps DESCONOCIDAS mostramos el tamaño total pero SIN sugerir borrar
nada — el usuario decide manualmente.
"""

import os
import sys
from pathlib import Path
from typing import Callable, List, Optional


# ============================================================
# Catálogo de apps conocidas
# ============================================================
# Cada entry:
#   name: nombre humano
#   kind: categoría (editor de video, comunicación, dev, etc.)
#   folder_names: nombres exactos de la carpeta dentro de AppData\Local o
#                 AppData\Roaming que identifican la app
#   location: "local", "roaming" o "both"
#   cleanable: lista de {subpath (glob), safety, desc}
#
# safety: "safe" | "caution" | "dangerous"

KNOWN_APPS = [
    # ============= EDITORES DE VIDEO =============
    {
        "name": "CapCut",
        "kind": "Editor de video",
        "folder_names": ["CapCut"],
        "location": "local",
        "cleanable": [
            {"subpath": "User Data/*/Cache", "safety": "safe",
             "desc": "Cache de la app — se regenera"},
            {"subpath": "User Data/*/Code Cache", "safety": "safe",
             "desc": "Cache del motor de render"},
            {"subpath": "User Data/*/GPUCache", "safety": "safe",
             "desc": "Cache de GPU"},
            {"subpath": "User Data/*/DraftCache", "safety": "safe",
             "desc": "Borradores en caché"},
            {"subpath": "User Data/*/CachedFiles", "safety": "safe",
             "desc": "Archivos cacheados de proyectos"},
            {"subpath": "User Data/*/preview_files", "safety": "safe",
             "desc": "Previews de video (se regeneran al abrir)"},
            {"subpath": "User Data/*/CacheStorage", "safety": "safe",
             "desc": "Storage temporal de la web view"},
            {"subpath": "Live/CacheData", "safety": "safe",
             "desc": "Cache del módulo de streaming en vivo"},
        ],
    },
    {
        "name": "DaVinci Resolve",
        "kind": "Editor de video",
        "folder_names": ["Blackmagic Design"],
        "location": "both",
        "cleanable": [
            {"subpath": "DaVinci Resolve/CacheClip", "safety": "safe",
             "desc": "Cache de clips renderizados"},
            {"subpath": "DaVinci Resolve/Support/Fusion/Cache", "safety": "safe",
             "desc": "Cache de composiciones Fusion"},
            {"subpath": "DaVinci Resolve/Logs", "safety": "safe",
             "desc": "Logs de la app"},
        ],
    },
    # ============= COMUNICACIÓN =============
    {
        "name": "Discord",
        "kind": "Comunicación",
        "folder_names": ["discord"],
        "location": "roaming",
        "cleanable": [
            {"subpath": "Cache", "safety": "safe", "desc": "Cache de mensajes e imágenes"},
            {"subpath": "Code Cache", "safety": "safe", "desc": "Cache del motor"},
            {"subpath": "GPUCache", "safety": "safe", "desc": "Cache de GPU"},
            {"subpath": "Service Worker/CacheStorage", "safety": "safe",
             "desc": "Cache del service worker"},
        ],
    },
    {
        "name": "Slack",
        "kind": "Comunicación",
        "folder_names": ["Slack"],
        "location": "roaming",
        "cleanable": [
            {"subpath": "Cache", "safety": "safe", "desc": "Cache de canales/mensajes"},
            {"subpath": "Code Cache", "safety": "safe", "desc": "Cache del motor"},
            {"subpath": "GPUCache", "safety": "safe", "desc": "Cache de GPU"},
            {"subpath": "Service Worker/CacheStorage", "safety": "safe",
             "desc": "Cache de service worker"},
        ],
    },
    {
        "name": "Microsoft Teams",
        "kind": "Comunicación",
        "folder_names": ["Microsoft/Teams", "Teams"],
        "location": "roaming",
        "cleanable": [
            {"subpath": "Cache", "safety": "safe", "desc": "Cache de mensajes"},
            {"subpath": "Code Cache", "safety": "safe", "desc": "Cache del motor"},
            {"subpath": "GPUCache", "safety": "safe", "desc": "Cache de GPU"},
            {"subpath": "Service Worker/CacheStorage", "safety": "safe",
             "desc": "Cache de service worker"},
        ],
    },
    {
        "name": "Zoom",
        "kind": "Comunicación",
        "folder_names": ["Zoom"],
        "location": "roaming",
        "cleanable": [
            {"subpath": "bin", "safety": "caution",
             "desc": "Versiones viejas del ejecutable — safe pero pueden re-descargarse"},
            {"subpath": "logs", "safety": "safe", "desc": "Logs de sesiones pasadas"},
        ],
    },
    # ============= CLOUD =============
    {
        "name": "Dropbox",
        "kind": "Cloud",
        "folder_names": ["Dropbox"],
        "location": "local",
        "cleanable": [
            {"subpath": "cache", "safety": "safe", "desc": "Cache de sync"},
            {"subpath": "l/storage", "safety": "safe", "desc": "Storage temporal"},
            {"subpath": "instance*/logs", "safety": "safe", "desc": "Logs"},
        ],
    },
    {
        "name": "Google Drive",
        "kind": "Cloud",
        "folder_names": ["Google/DriveFS"],
        "location": "local",
        "cleanable": [
            {"subpath": "Logs", "safety": "safe", "desc": "Logs"},
        ],
    },
    # ============= STREAMING / MEDIA =============
    {
        "name": "Spotify",
        "kind": "Música",
        "folder_names": ["Spotify"],
        "location": "local",
        "cleanable": [
            {"subpath": "Data", "safety": "caution",
             "desc": "Cache de canciones descargadas — se re-descargan al escuchar"},
            {"subpath": "User/*/local-files.bnk", "safety": "safe",
             "desc": "Banco de archivos locales"},
        ],
    },
    {
        "name": "OBS Studio",
        "kind": "Streaming",
        "folder_names": ["obs-studio"],
        "location": "roaming",
        "cleanable": [
            {"subpath": "logs", "safety": "safe", "desc": "Logs"},
            {"subpath": "crashes", "safety": "safe", "desc": "Reportes de crash"},
        ],
    },
    # ============= DEV =============
    {
        "name": "VS Code",
        "kind": "Desarrollo",
        "folder_names": ["Code"],
        "location": "roaming",
        "cleanable": [
            {"subpath": "Cache", "safety": "safe", "desc": "Cache de UI"},
            {"subpath": "Code Cache", "safety": "safe", "desc": "Cache del engine"},
            {"subpath": "GPUCache", "safety": "safe", "desc": "Cache de GPU"},
            {"subpath": "logs", "safety": "safe", "desc": "Logs"},
            {"subpath": "CachedData", "safety": "safe", "desc": "Data cacheada"},
            {"subpath": "CachedExtensions", "safety": "safe", "desc": "Cache de extensiones"},
            {"subpath": "Service Worker/CacheStorage", "safety": "safe",
             "desc": "Service worker cache"},
        ],
    },
    {
        "name": "Docker Desktop",
        "kind": "Desarrollo",
        "folder_names": ["Docker"],
        "location": "local",
        "cleanable": [
            {"subpath": "log", "safety": "safe", "desc": "Logs"},
        ],
    },
    # ============= ADOBE =============
    {
        "name": "Adobe (general)",
        "kind": "Diseño",
        "folder_names": ["Adobe"],
        "location": "roaming",
        "cleanable": [
            {"subpath": "OOBE/Cache", "safety": "safe", "desc": "Cache del instalador"},
            {"subpath": "Common/Media Cache Files", "safety": "safe",
             "desc": "Media cache global de Adobe"},
        ],
    },
]


# ============================================================
# Análisis
# ============================================================

def _tree_size(path: Path) -> int:
    """Suma bytes de todos los archivos en path."""
    total = 0
    try:
        for dirpath, dirs, files in os.walk(path, followlinks=False):
            for f in files:
                try:
                    total += os.lstat(os.path.join(dirpath, f)).st_size
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def _resolve_globs(base: Path, subpath: str) -> List[Path]:
    """Expande '*' del subpath. Devuelve list de paths existentes."""
    import glob
    pattern = str(base / subpath.replace("/", os.sep))
    return [Path(m) for m in glob.glob(pattern) if Path(m).exists()]


def analyze_app(app: dict,
                appdata_local: Path,
                appdata_roaming: Path,
                on_progress: Optional[Callable[[str], None]] = None) -> Optional[dict]:
    """
    Chequea si esta app existe en AppData y calcula tamaños.
    Devuelve dict {name, kind, location, total_size, cleanable_size, cleanable_items}
    o None si la app no está instalada.
    """
    # Buscar la carpeta base de la app en cada location aplicable
    base_paths = []
    for folder_name in app["folder_names"]:
        loc = app["location"]
        if loc in ("local", "both"):
            p = appdata_local / folder_name.replace("/", os.sep)
            if p.exists():
                base_paths.append(("local", p))
        if loc in ("roaming", "both"):
            p = appdata_roaming / folder_name.replace("/", os.sep)
            if p.exists():
                base_paths.append(("roaming", p))
    if not base_paths:
        return None

    total_size = 0
    cleanable_items = []
    cleanable_size = 0
    for _loc, base in base_paths:
        if on_progress:
            on_progress(f"Midiendo {app['name']} en {base.name}…")
        total_size += _tree_size(base)
        # Cleanable subfolders
        for c in app["cleanable"]:
            matches = _resolve_globs(base, c["subpath"])
            for m in matches:
                sz = _tree_size(m)
                if sz > 0:
                    cleanable_items.append({
                        "path": m,
                        "size": sz,
                        "safety": c["safety"],
                        "desc": c["desc"],
                        "subpath": c["subpath"],
                    })
                    cleanable_size += sz
    if total_size == 0 and not cleanable_items:
        return None

    return {
        "name": app["name"],
        "kind": app["kind"],
        "total_size": total_size,
        "cleanable_size": cleanable_size,
        "cleanable_items": cleanable_items,
        "base_paths": [str(p) for _, p in base_paths],
    }


def analyze_all(on_progress: Optional[Callable[[str], None]] = None) -> List[dict]:
    """
    Escanea todas las apps conocidas. Devuelve list ordenada por cleanable_size desc.
    Solo apps que estén realmente instaladas (con datos en AppData).
    """
    if not sys.platform.startswith("win"):
        # En Mac los paths son distintos — usamos ~/Library/Application Support
        # Por ahora este módulo es Windows-first. Mac usa las cats de macOS existentes.
        return []
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    roaming = Path(os.environ.get("APPDATA", ""))
    if not local.exists() or not roaming.exists():
        return []

    results = []
    for app in KNOWN_APPS:
        r = analyze_app(app, local, roaming, on_progress=on_progress)
        if r:
            results.append(r)
    results.sort(key=lambda x: -x["cleanable_size"])
    return results
