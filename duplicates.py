"""
Detector de archivos duplicados.

Estrategia:
  1. Recorrer las carpetas raíz (por defecto: Descargas, Documentos, Escritorio).
  2. Agrupar archivos por tamaño (dos archivos con distinto tamaño no pueden
     ser duplicados). Ignorar archivos por debajo de min_size.
  3. Para cada grupo con 2+ archivos del mismo tamaño, calcular un hash rápido
     de los primeros 4 KB. Si sigue habiendo colisión, hash completo (SHA-1).
  4. Devolver grupos de archivos verdaderamente idénticos.

Esta estrategia (size → head-hash → full-hash) evita leer archivos completos
cuando no hace falta.
"""

import hashlib
import os
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional


class ScanCancel:
    """Flag para cancelar un scan largo desde otro thread."""

    def __init__(self):
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

HOME = Path.home()

# Roots cross-platform (Movies en Mac, Videos en Windows)
def _default_roots():
    from platform_helpers import default_duplicate_roots
    return default_duplicate_roots()

DEFAULT_ROOTS = _default_roots()

# Ignorar rutas que contengan estos fragmentos (paquetes, bundles, apps, git)
_SKIP_FRAGMENTS = (
    "/.git/", "/node_modules/", "/.venv/", "/venv/", "/__pycache__/",
    "/Library/", "/.Trash/", ".app/Contents/",
)

# Extensiones que solemos NO querer deduplicar
_SKIP_EXTS = {".plist", ".sqlite", ".sqlite-wal", ".sqlite-shm", ".lock"}


def _should_skip(p: Path) -> bool:
    ps = str(p)
    if any(frag in ps for frag in _SKIP_FRAGMENTS):
        return True
    if p.suffix.lower() in _SKIP_EXTS:
        return True
    if p.name.startswith("."):
        return True
    return False


def _walk_files(root: Path, min_size: int, skip_symlinks: bool = True):
    if not root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # No descender dentro de .app o carpetas raras
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and not d.endswith(".app")
            and d not in ("node_modules", "__pycache__", ".venv", "venv")
        ]
        for name in filenames:
            fp = Path(dirpath) / name
            try:
                if skip_symlinks and fp.is_symlink():
                    continue
                if _should_skip(fp):
                    continue
                size = fp.stat().st_size
                if size < min_size:
                    continue
                yield fp, size
            except (OSError, PermissionError):
                continue


def _hash_head(path: Path, size: int = 4096) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            return hashlib.sha1(f.read(size)).hexdigest()
    except OSError:
        return None


def _hash_full(path: Path, chunk: int = 1 << 20) -> Optional[str]:
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            while True:
                b = f.read(chunk)
                if not b:
                    break
                h.update(b)
        return h.hexdigest()
    except OSError:
        return None


def find_duplicates(
    roots: Optional[List[Path]] = None,
    min_size: int = 1024 * 1024,   # 1 MB por defecto (evita ruido)
    on_progress: Optional[Callable[[str], None]] = None,
    on_group_found: Optional[Callable[[List[Path]], None]] = None,
    cancel: Optional[ScanCancel] = None,
) -> List[List[Path]]:
    """
    Devuelve una lista de grupos. Cada grupo es una lista de rutas
    de archivos con contenido idéntico (2 o más).

    Streaming:
      - on_group_found: se llama para CADA grupo confirmado, así la UI
        puede mostrarlos a medida que aparecen sin esperar el fin del scan.
      - cancel: si el flag se activa, la función corta y devuelve los
        resultados parciales ya encontrados.
    """
    if roots is None:
        roots = DEFAULT_ROOTS

    if on_progress:
        on_progress("Recorriendo carpetas…")
    by_size: Dict[int, List[Path]] = defaultdict(list)
    seen = 0
    for root in roots:
        if cancel and cancel.is_cancelled():
            return []
        for path, size in _walk_files(root, min_size=min_size):
            by_size[size].append(path)
            seen += 1
            if on_progress and seen % 500 == 0:
                on_progress(f"Recorridos {seen:,} archivos…")
            if cancel and cancel.is_cancelled():
                return []

    # Solo grupos con 2+ archivos del mismo tamaño
    candidates = {s: ps for s, ps in by_size.items() if len(ps) > 1}

    if on_progress:
        on_progress(f"Comparando {sum(len(v) for v in candidates.values()):,} candidatos…")

    # Nivel 2: hash de la cabeza (primeros 4 KB)
    by_head: Dict[tuple, List[Path]] = defaultdict(list)
    for size, paths in candidates.items():
        if cancel and cancel.is_cancelled():
            return []
        for p in paths:
            h = _hash_head(p)
            if h is not None:
                by_head[(size, h)].append(p)

    head_groups = [ps for ps in by_head.values() if len(ps) > 1]

    if on_progress:
        on_progress(f"Verificando {sum(len(g) for g in head_groups):,} candidatos "
                    "con hash completo…")

    # Nivel 3: hash completo para confirmar. Emitimos cada grupo confirmado
    # al vuelo (streaming) para que la UI pueda mostrarlo enseguida.
    result: List[List[Path]] = []
    total_head = len(head_groups)
    for idx, group in enumerate(head_groups, 1):
        if cancel and cancel.is_cancelled():
            break
        if on_progress and idx % 5 == 0:
            on_progress(f"Verificando {idx}/{total_head} grupos…")
        by_full: Dict[str, List[Path]] = defaultdict(list)
        for p in group:
            if cancel and cancel.is_cancelled():
                break
            fh = _hash_full(p)
            if fh is not None:
                by_full[fh].append(p)
        for ps in by_full.values():
            if len(ps) > 1:
                confirmed = sorted(ps, key=lambda x: str(x))
                result.append(confirmed)
                if on_group_found:
                    on_group_found(confirmed)

    # Ordenar por tamaño total desperdiciado (mas grande primero)
    def wasted(group):
        try:
            single = group[0].stat().st_size
        except OSError:
            return 0
        return single * (len(group) - 1)

    result.sort(key=wasted, reverse=True)
    return result
