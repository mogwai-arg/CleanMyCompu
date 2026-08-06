"""
Historial de limpiezas.

Persiste un registro de cada operación de limpieza (categoría, bytes liberados,
items borrados, fecha) en un JSON en ~/.cleanmycompu/stats.json.

Usado por la sección "Estadísticas" para mostrar el impacto acumulado.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

_STATS_DIR = Path.home() / ".cleanmycompu"
_STATS_FILE = _STATS_DIR / "stats.json"


def _load() -> list:
    if not _STATS_FILE.exists():
        return []
    try:
        return json.loads(_STATS_FILE.read_text())
    except Exception:
        return []


def _save(records: list):
    try:
        _STATS_DIR.mkdir(parents=True, exist_ok=True)
        _STATS_FILE.write_text(json.dumps(records))
    except Exception:
        pass


def record(source: str, bytes_freed: int, items: int = 0):
    """
    Registra una operación de limpieza.
      - source: nombre de la sección/categoría (ej. "Sistema", "Duplicados", "Adobe leftovers")
      - bytes_freed: bytes liberados
      - items: cantidad de archivos borrados (opcional)
    Nunca lanza excepción.
    """
    if bytes_freed <= 0:
        return
    records = _load()
    records.append({
        "date": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "bytes": int(bytes_freed),
        "items": int(items),
    })
    # Mantener solo los últimos 2000 registros (evita crecimiento infinito)
    if len(records) > 2000:
        records = records[-2000:]
    _save(records)


def all_records() -> list:
    return _load()


def summary() -> dict:
    """
    Devuelve resumen: total, últimos 30 días, distribución por fuente, top 10 recientes.
    """
    records = _load()
    total_bytes = sum(r["bytes"] for r in records)
    total_items = sum(r.get("items", 0) for r in records)
    total_ops = len(records)

    cutoff = (datetime.now() - timedelta(days=30)).timestamp()

    def _ts(r):
        try:
            return datetime.fromisoformat(r["date"]).timestamp()
        except Exception:
            return 0

    recent = [r for r in records if _ts(r) >= cutoff]
    recent_bytes = sum(r["bytes"] for r in recent)
    recent_items = sum(r.get("items", 0) for r in recent)
    recent_ops = len(recent)

    # Distribución por source
    by_source = {}
    for r in records:
        s = r.get("source", "?")
        by_source[s] = by_source.get(s, 0) + r["bytes"]
    by_source_sorted = sorted(by_source.items(), key=lambda x: -x[1])

    # Últimos 10 (para timeline)
    latest = list(reversed(records[-10:]))

    return {
        "total_bytes": total_bytes,
        "total_items": total_items,
        "total_ops": total_ops,
        "recent_bytes": recent_bytes,
        "recent_items": recent_items,
        "recent_ops": recent_ops,
        "by_source": by_source_sorted,
        "latest": latest,
        "first_use": records[0]["date"] if records else None,
    }


def reset():
    """Borra todo el historial. Nunca lanza excepción."""
    try:
        if _STATS_FILE.exists():
            _STATS_FILE.unlink()
    except Exception:
        pass
