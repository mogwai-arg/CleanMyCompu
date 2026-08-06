"""
Escáner: mide cuánto ocupa cada categoría de limpieza.
NUNCA borra nada. Solo lee tamaños.
"""

import glob
import os
import time
from pathlib import Path
from typing import List, Tuple


def resolve_paths(patterns: List[str], min_age_days: int = 0) -> List[Path]:
    """
    Convierte patrones (con ~ y *) en rutas reales que existen en el disco.
    Ej: "~/Library/Caches" -> [Path("/Users/Javi/Library/Caches")]
        "~/Library/Application Support/Firefox/Profiles/*/cache2"
          -> [Path(".../Profiles/abc.default/cache2"), ...]

    Si min_age_days > 0, filtra los resultados y solo devuelve rutas cuyo
    mtime sea más viejo que ese umbral (útil para "descargas viejas").
    """
    resolved = []
    seen = set()
    for pattern in patterns:
        # Expandir ~ (Unix) y %VAR% (Windows) y $VAR
        expanded = os.path.expandvars(os.path.expanduser(pattern))
        matches = glob.glob(expanded) if any(c in expanded for c in "*?[") else [expanded]
        for m in matches:
            try:
                p = Path(m).resolve()
            except OSError:
                continue
            if p.exists() and str(p) not in seen:
                seen.add(str(p))
                resolved.append(p)

    if min_age_days > 0:
        cutoff = time.time() - (min_age_days * 86400)
        filtered = []
        for p in resolved:
            try:
                if p.stat().st_mtime < cutoff:
                    filtered.append(p)
            except OSError:
                pass
        resolved = filtered

    return resolved


def directory_size(path: Path) -> Tuple[int, int]:
    """
    Recorre una carpeta y devuelve (bytes totales, cantidad de archivos).
    Ignora enlaces simbólicos y archivos a los que no tiene permiso.
    """
    total_bytes = 0
    file_count = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    st = os.lstat(fp)
                    # No sumar symlinks
                    if not os.path.islink(fp):
                        total_bytes += st.st_size
                        file_count += 1
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total_bytes, file_count


def get_paths_for_category(category: dict) -> List[Path]:
    """
    Devuelve las rutas a escanear/limpiar de una categoría.
    Soporta dos modos:
      - path_patterns (estático, con globs)
      - path_provider (dinámico, llama a una función de leftovers.PROVIDERS)
    """
    if "path_provider" in category:
        from leftovers import PROVIDERS
        provider = PROVIDERS.get(category["path_provider"])
        if provider is None:
            return []
        try:
            return provider()
        except Exception:
            return []
    return resolve_paths(
        category.get("path_patterns", []),
        min_age_days=category.get("min_age_days", 0),
    )


def scan_category(category: dict) -> dict:
    """
    Escanea una categoría y devuelve un diccionario con el resultado.
    """
    paths = get_paths_for_category(category)
    total_bytes = 0
    total_files = 0
    for p in paths:
        if p.is_dir():
            b, c = directory_size(p)
            total_bytes += b
            total_files += c
        elif p.is_file():
            try:
                total_bytes += p.stat().st_size
                total_files += 1
            except OSError:
                pass
    return {
        "id": category["id"],
        "group": category.get("group", "Otros"),
        "name": category["name"],
        "icon": category.get("icon", "•"),
        "description": category["description"],
        "safety": category.get("safety", "safe"),
        "bytes": total_bytes,
        "file_count": total_files,
        "resolved_paths": [str(p) for p in paths],
    }
