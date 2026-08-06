"""
Analizador de disco — te muestra qué carpetas ocupan más espacio.

Escanea recursivamente subcarpetas de primer nivel de un drive/carpeta y
suma sus tamaños. Devuelve un ranking ordenado que responde la pregunta
"¿qué me está llenando el disco?".
"""

import os
from pathlib import Path
from typing import Callable, List, Optional

# Carpetas que NUNCA escaneamos (system-locked, symlinks a otras cosas, etc.)
_SKIP_NAMES = {
    # Windows
    "System Volume Information", "$Recycle.Bin", "PerfLogs",
    "hiberfil.sys", "pagefile.sys", "swapfile.sys", "DumpStack.log.tmp",
    # macOS
    ".Spotlight-V100", ".Trashes", ".fseventsd", ".DocumentRevisions-V100",
}


def _folder_size(path: Path,
                 on_progress: Optional[Callable[[str], None]] = None,
                 stop_check: Optional[Callable[[], bool]] = None) -> int:
    """Suma bytes de todos los archivos dentro de path, recursivo."""
    total = 0
    counter = [0]
    try:
        for dirpath, dirs, files in os.walk(path, followlinks=False):
            # Cortar recursión en carpetas system
            dirs[:] = [d for d in dirs if d not in _SKIP_NAMES]
            if stop_check and stop_check():
                return total
            for f in files:
                if f in _SKIP_NAMES:
                    continue
                fp = os.path.join(dirpath, f)
                try:
                    total += os.lstat(fp).st_size
                    counter[0] += 1
                    if on_progress and counter[0] % 500 == 0:
                        on_progress(f"{path.name}: {counter[0]:,} archivos…")
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def top_folders(root,
                top_n: int = 20,
                on_progress: Optional[Callable[[str], None]] = None,
                stop_check: Optional[Callable[[], bool]] = None) -> List[dict]:
    """
    Top-N subcarpetas de primer nivel de `root`, ordenadas desc por tamaño.
    Devuelve list de {path, name, size} en bytes.
    """
    root = Path(root)
    results = []
    try:
        entries = list(root.iterdir())
    except (OSError, PermissionError):
        return []

    for entry in entries:
        if stop_check and stop_check():
            break
        try:
            if entry.is_symlink():
                continue
            if entry.name in _SKIP_NAMES:
                continue
            if entry.name.startswith("."):
                # Skipear dotfiles/dotdirs excepto los "de peso" del usuario
                if entry.name not in (".cache", ".npm", ".gradle", ".m2"):
                    continue
            if on_progress:
                on_progress(f"Midiendo: {entry.name}")
            if entry.is_dir():
                size = _folder_size(entry, on_progress=on_progress, stop_check=stop_check)
                if size > 0:
                    results.append({
                        "path": entry, "name": entry.name, "size": size,
                        "kind": "folder",
                    })
            elif entry.is_file():
                try:
                    size = entry.stat().st_size
                    if size > 1024 * 1024:  # archivos sueltos >1MB
                        results.append({
                            "path": entry, "name": entry.name, "size": size,
                            "kind": "file",
                        })
                except OSError:
                    pass
        except (OSError, PermissionError):
            continue

    results.sort(key=lambda x: -x["size"])
    return results[:top_n]
