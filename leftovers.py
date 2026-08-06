"""
Detector de restos de apps desinstaladas.

Funciona así:
  1. Lista todas las apps instaladas (/Applications, /System/Applications, ~/Applications)
     y lee su CFBundleIdentifier (ej. "com.google.chrome").
  2. Recorre carpetas de ~/Library donde macOS y las apps guardan datos.
  3. Cualquier archivo o carpeta cuyo nombre parezca un bundle ID (ej.
     "com.spotify.client.plist") pero NO corresponda a ninguna app instalada
     se considera un "huérfano" — probablemente restos de una app que
     desinstalaste o de una versión vieja.

Es una heurística: puede haber falsos positivos, por eso el módulo lo marca
como "caution" y NO se selecciona por defecto en la UI.
"""

import plistlib
from pathlib import Path
from typing import List, Optional, Set

HOME = Path.home()

# Prefijos del sistema — nunca los consideramos huérfanos.
SYSTEM_PREFIXES = (
    "com.apple.",
    "group.com.apple.",
    "systemgroup.com.apple.",
    "loginwindow",
    ".globalpreferences",
    "org.python.",
    "org.pyside",
    "com.qt.",
)

# Nombres que aunque parezcan bundle IDs no lo son, o son propios del sistema.
NOT_BUNDLE_IDS = {
    "byhost",
    "macos",
    "extensions",
    "audio",
    "video",
}

# Carpetas donde buscar restos.
SEARCH_DIRS = [
    HOME / "Library" / "Preferences",
    HOME / "Library" / "Application Support",
    HOME / "Library" / "Caches",
    HOME / "Library" / "Containers",
    HOME / "Library" / "HTTPStorages",
    HOME / "Library" / "Saved Application State",
    HOME / "Library" / "WebKit",
]


def _read_bundle_id(plist_path: Path) -> Optional[str]:
    try:
        with open(plist_path, "rb") as f:
            data = plistlib.load(f)
        val = data.get("CFBundleIdentifier")
        return val if isinstance(val, str) else None
    except Exception:
        return None


def _iter_apps(base: Path, max_depth: int = 3, cur_depth: int = 0):
    """Iterar .app bundles bajo `base` sin descender dentro de un .app."""
    try:
        entries = list(base.iterdir())
    except OSError:
        return
    for e in entries:
        if e.name.endswith(".app"):
            yield e
        elif e.is_dir() and cur_depth < max_depth and not e.name.startswith("."):
            yield from _iter_apps(e, max_depth, cur_depth + 1)


def get_installed_bundle_ids() -> Set[str]:
    """Bundle IDs (lowercase) de todas las apps instaladas."""
    app_dirs = [
        Path("/Applications"),
        Path("/System/Applications"),
        HOME / "Applications",
    ]
    ids: Set[str] = set()
    for base in app_dirs:
        if not base.exists():
            continue
        for app in _iter_apps(base):
            plist = app / "Contents" / "Info.plist"
            if plist.exists():
                bid = _read_bundle_id(plist)
                if bid:
                    ids.add(bid.lower())
    return ids


import re

# Bundle ID válido en macOS: caracteres alfanuméricos y guiones, separados por puntos.
# No permite espacios ni empieza con dígito en el primer segmento.
_BUNDLE_ID_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9-]*(\.[a-zA-Z0-9-]+)+$")


def _candidate_bundle_id(entry_name: str) -> Optional[str]:
    """
    Extrae un posible bundle ID del nombre de un archivo/carpeta en Library.
    Devuelve None si no parece ser un bundle ID.
    """
    name = entry_name
    for ext in (".plist", ".savedState", ".sfl2", ".sfl3", ".binarycookies", ".lockfile"):
        if name.endswith(ext):
            name = name[: -len(ext)]
            break

    # Debe matchear el patrón reverse-DNS estricto (sin espacios, no versiones)
    if not _BUNDLE_ID_RE.match(name):
        return None

    lname = name.lower()

    if lname in NOT_BUNDLE_IDS:
        return None
    for prefix in SYSTEM_PREFIXES:
        if lname.startswith(prefix):
            return None

    # Filtrar segmentos numéricos que serían versiones (ej. "foo.30.6.0")
    # Un bundle ID legítimo no tiene segmentos que sean puramente numéricos
    # excepto quizás como sufijo raro. Filtramos si HAY numérico puro en medio.
    parts = lname.split(".")
    if any(p.isdigit() for p in parts):
        return None

    return lname


def find_orphaned_paths() -> List[Path]:
    """
    Escanea carpetas de Library y devuelve las rutas que parecen ser
    de apps NO instaladas actualmente.
    """
    installed = get_installed_bundle_ids()

    # "Familias" de bundle IDs — si tenés com.adobe.photoshop instalado,
    # asumimos que otros com.adobe.* pertenecen a Adobe y NO son huérfanos.
    families: Set[str] = set()
    for bid in installed:
        parts = bid.split(".")
        if len(parts) >= 2:
            families.add(f"{parts[0]}.{parts[1]}")

    orphans: List[Path] = []
    seen = set()
    for base in SEARCH_DIRS:
        if not base.exists():
            continue
        try:
            entries = list(base.iterdir())
        except OSError:
            continue
        for entry in entries:
            candidate = _candidate_bundle_id(entry.name)
            if candidate is None:
                continue
            if candidate in installed:
                continue
            parts = candidate.split(".")
            fam = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else None
            if fam and fam in families:
                continue
            # ¿Es un sub-namespace de una app instalada? ej. com.foo.bar.helper si com.foo.bar existe
            if any(candidate.startswith(iid + ".") for iid in installed):
                continue

            key = str(entry.resolve()) if entry.exists() else str(entry)
            if key in seen:
                continue
            seen.add(key)
            orphans.append(entry)
    return orphans


# Registro de proveedores dinámicos.
# Una categoría con "path_provider": "orphaned_app_data" en targets.py
# llamará a esta función en vez de usar path_patterns.
PROVIDERS = {
    "orphaned_app_data": find_orphaned_paths,
}
