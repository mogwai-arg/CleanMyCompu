"""
Detector de archivos grandes olvidados.

Escanea carpetas de usuario buscando archivos que:
  - Pesen más de min_size (100 MB por defecto)
  - No hayan sido accedidos hace más de min_age_days (180 = 6 meses)

Devuelve lista de archivos con path, size, last accessed date, para que el
usuario elija cuáles borrar.
"""

import os
import time
from pathlib import Path
from typing import Callable, List, Optional

HOME = Path.home()


def _default_roots():
    from platform_helpers import default_large_file_roots
    return default_large_file_roots()


DEFAULT_ROOTS = _default_roots()

_SKIP_FRAGMENTS = (
    "/.git/", "/node_modules/", "/.venv/", "/venv/",
    "/Library/", "/.Trash/", ".app/Contents/",
    "/iCloud", "/OneDrive",
)


def find_large_files(
    roots: Optional[List[Path]] = None,
    min_size: int = 100 * 1024 * 1024,   # 100 MB
    min_age_days: int = 180,             # 6 meses sin abrir
    on_progress: Optional[Callable[[str], None]] = None,
) -> List[dict]:
    """
    Devuelve lista de dicts: {path, size, atime}
    Ordenados por tamaño descendente.
    """
    if roots is None:
        roots = DEFAULT_ROOTS

    cutoff = time.time() - (min_age_days * 86400)
    results = []
    scanned = 0

    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            # No descender en carpetas del sistema/paquetes
            dirnames[:] = [d for d in dirnames
                           if not d.startswith(".")
                           and not d.endswith(".app")
                           and d not in ("node_modules", "__pycache__", ".venv")]
            if any(frag in dirpath for frag in _SKIP_FRAGMENTS):
                continue
            for name in filenames:
                if name.startswith("."):
                    continue
                fp = Path(dirpath) / name
                try:
                    if fp.is_symlink():
                        continue
                    st = fp.stat()
                    if st.st_size < min_size:
                        continue
                    if st.st_atime > cutoff:
                        continue  # accedido recientemente
                    results.append({
                        "path": fp,
                        "size": st.st_size,
                        "atime": st.st_atime,
                    })
                except (OSError, PermissionError):
                    continue
                scanned += 1
                if on_progress and scanned % 200 == 0:
                    on_progress(f"Escaneados {scanned:,} candidatos…")

    results.sort(key=lambda x: -x["size"])
    return results
