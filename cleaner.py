"""
Limpiador: borra los archivos que el escáner detectó.
Estrategia:
  - Para cada ruta, borra el CONTENIDO (archivos y subcarpetas), pero conserva
    la carpeta padre. Esto evita romper apps que asumen que la carpeta existe.
  - Errores por archivos bloqueados o sin permiso se ignoran silenciosamente,
    para que un único archivo problemático no aborte toda la limpieza.
  - Por defecto borra permanentemente (los caches son regenerables, no tiene
    sentido llenar la Papelera con basura).
"""

import os
import shutil
from pathlib import Path
from typing import Callable, List, Optional


def _size_of(path: Path) -> int:
    """Tamaño en bytes de un archivo o de una carpeta completa."""
    if path.is_symlink():
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.lstat(fp).st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _delete_one(path: Path, mode: str, progress: Optional[Callable[[str], None]]) -> int:
    """
    Borra un solo elemento (archivo o carpeta) y devuelve el tamaño liberado.
    Nunca lanza excepción hacia afuera.
    """
    try:
        size = _size_of(path)
        if mode == "trash":
            from send2trash import send2trash
            send2trash(str(path))
        else:  # permanent
            if path.is_symlink() or path.is_file():
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
        if progress:
            progress(f"Borrado: {path.name}")
        return size
    except Exception:
        return 0


def clean_paths(
    paths: List[Path],
    mode: str = "permanent",
    progress: Optional[Callable[[str], None]] = None,
) -> int:
    """
    Borra el contenido de cada ruta.
      - Si la ruta es una carpeta: borra sus hijos (files y subdirs), pero
        conserva la carpeta misma.
      - Si la ruta es un archivo: lo borra directamente.

    mode:
      - "permanent" (default): borrado definitivo. Recomendado para caches/logs.
      - "trash": mueve a la Papelera. Recuperable pero NO libera espacio hasta
        vaciar la Papelera.

    Devuelve total de bytes liberados.
    """
    freed = 0
    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        if path.is_dir():
            try:
                children = list(path.iterdir())
            except OSError:
                continue
            for child in children:
                freed += _delete_one(child, mode, progress)
        else:
            freed += _delete_one(path, mode, progress)
    return freed
