"""
Detección de fotos similares/duplicadas usando perceptual hash (pHash).

A diferencia de duplicates.py (que busca archivos byte-a-byte idénticos),
esto encuentra fotos VISUALMENTE parecidas aunque tengan tamaño distinto:
  - Misma foto redimensionada
  - Misma foto en distintos formatos (jpg vs heic)
  - Fotos casi idénticas (ligeras ediciones, filtros)

Algoritmo:
  1. Recorrer directorio buscando imágenes
  2. Calcular pHash de cada una (64-bit hash)
  3. Agrupar por hash idéntico (exacto) o Hamming distance <= threshold
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

# imagehash + PIL son las libs standard para esto
try:
    from PIL import Image
    import imagehash
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False


IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".heic", ".heif",
    ".bmp", ".tiff", ".tif", ".webp",
}


class ScanCancel:
    """Objeto que permite cancelar el scan desde afuera. Igual que duplicates.py."""
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self.cancelled


def is_available() -> bool:
    """True si imagehash + PIL están instalados."""
    return HAS_IMAGEHASH


def default_photo_dirs() -> List[Path]:
    """Directorios estándar donde suele haber fotos, según OS."""
    home = Path.home()
    candidates = [
        home / "Pictures",
        home / "Fotos",  # locale ES
        home / "Imágenes",  # locale ES Win
        home / "Desktop",
    ]
    return [d for d in candidates if d.exists()]


def _phash(path: Path) -> Optional[str]:
    """Calcula perceptual hash de una imagen. Devuelve None si falla."""
    try:
        with Image.open(path) as img:
            # phash es más robusto ante compresión/reescalado que ahash
            h = imagehash.phash(img, hash_size=8)
            return str(h)
    except Exception:
        return None


def find_similar(
    directories: List[Path],
    threshold: int = 5,
    min_size_kb: int = 30,
    on_progress: Optional[Callable[[str], None]] = None,
    on_group_found: Optional[Callable[[dict], None]] = None,
    cancel: Optional[ScanCancel] = None,
) -> List[dict]:
    """
    Escanea imágenes en `directories`, agrupa las visualmente similares.

    threshold: distancia Hamming máxima para considerar 2 fotos similares.
      0 = idénticas visualmente (ideal para duplicados exactos)
      5 = muy parecidas (misma foto reescalada, con filtros suaves)
      10 = parecidas (mismo motivo, edición fuerte)

    Devuelve lista de grupos:
      [{"hash": "...", "items": [{"path": Path, "size": int, "mtime": datetime}], "total_size": int}, ...]
    """
    if not HAS_IMAGEHASH:
        return []

    def _p(msg):
        if on_progress:
            on_progress(msg)

    # Fase 1: enumerar archivos
    _p("Buscando imágenes…")
    all_images: List[Path] = []
    min_bytes = min_size_kb * 1024
    for d in directories:
        if not d.exists():
            continue
        try:
            for f in d.rglob("*"):
                if cancel and cancel.is_cancelled:
                    return _finalize_groups(all_images, [])
                try:
                    if not f.is_file():
                        continue
                    if f.suffix.lower() not in IMAGE_EXTS:
                        continue
                    if f.stat().st_size < min_bytes:
                        continue
                    all_images.append(f)
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            continue

    _p(f"{len(all_images)} imágenes encontradas. Calculando hashes…")

    # Fase 2: calcular hash de cada imagen
    hashes: dict = {}  # hash_str → list de {path, size, mtime, hash_obj}
    for i, img in enumerate(all_images):
        if cancel and cancel.is_cancelled:
            break
        if i % 20 == 0:
            _p(f"Procesadas {i}/{len(all_images)}…")
        h_str = _phash(img)
        if h_str is None:
            continue
        try:
            st = img.stat()
            info = {
                "path": img,
                "size": st.st_size,
                "mtime": datetime.fromtimestamp(st.st_mtime),
                "hash": h_str,
            }
        except OSError:
            continue
        hashes.setdefault(h_str, []).append(info)

    # Fase 3: agrupar por similitud (para threshold > 0)
    # Estrategia simple: agrupamos por hash idéntico primero, luego mergeamos
    # grupos con distancia Hamming <= threshold.
    _p("Agrupando por similitud…")
    groups_map: dict = {}  # hash_str → dict del grupo
    for h_str, items in hashes.items():
        if len(items) >= 1:
            # Buscar si hay grupo existente cercano (dist <= threshold)
            merged = False
            if threshold > 0:
                target_hash = imagehash.hex_to_hash(h_str)
                for existing_h, group in groups_map.items():
                    existing_hash = imagehash.hex_to_hash(existing_h)
                    dist = target_hash - existing_hash
                    if dist <= threshold:
                        group["items"].extend(items)
                        merged = True
                        break
            if not merged:
                groups_map[h_str] = {"hash": h_str, "items": list(items)}

    # Filtrar grupos con >= 2 items (los únicos "duplicados/similares")
    groups = [g for g in groups_map.values() if len(g["items"]) >= 2]

    # Calcular total_size y ordenar items dentro de cada grupo
    for g in groups:
        g["items"].sort(key=lambda x: -x["size"])
        g["total_size"] = sum(x["size"] for x in g["items"])
        # Estimar recuperable: todo menos el más grande (asumiendo que el user
        # se queda con la mejor calidad = archivo más grande)
        g["recoverable"] = g["total_size"] - g["items"][0]["size"]
        if on_group_found:
            on_group_found(g)

    # Ordenar por recuperable desc
    groups.sort(key=lambda g: -g["recoverable"])
    _p(f"Listo. {len(groups)} grupos de fotos similares encontrados.")
    return groups


def _finalize_groups(all_imgs, done):
    """Placeholder para futuro — retorna lo que haya cuando se cancela."""
    return []
