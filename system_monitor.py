"""
Monitor del sistema en tiempo real: CPU, RAM, disco, batería, red.
Cross-platform vía psutil.

Cada función devuelve un dict listo para usar en la UI.
Todas son rápidas (<10ms típicamente) — safe para llamar en un QTimer cada segundo.
"""

import sys
from pathlib import Path
from typing import List, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def get_cpu() -> dict:
    """
    Uso de CPU total + por core.
    percent es el uso desde la última llamada (o desde arranque la primera vez).
    """
    if not HAS_PSUTIL:
        return {"percent": 0, "per_core": [], "count": 0, "freq_mhz": 0}
    percent = psutil.cpu_percent(interval=None)  # non-blocking
    per_core = psutil.cpu_percent(interval=None, percpu=True)
    freq = psutil.cpu_freq()
    return {
        "percent": percent,
        "per_core": per_core or [],
        "count": psutil.cpu_count(logical=True) or 0,
        "physical_count": psutil.cpu_count(logical=False) or 0,
        "freq_mhz": int(freq.current) if freq else 0,
    }


def get_ram() -> dict:
    """RAM total, usada, disponible y swap."""
    if not HAS_PSUTIL:
        return {"total": 0, "used": 0, "available": 0, "percent": 0,
                "swap_total": 0, "swap_used": 0, "swap_percent": 0}
    v = psutil.virtual_memory()
    s = psutil.swap_memory()
    return {
        "total": v.total,
        "used": v.used,
        "available": v.available,
        "percent": v.percent,
        "swap_total": s.total,
        "swap_used": s.used,
        "swap_percent": s.percent,
    }


def get_disks() -> List[dict]:
    """Lista de discos con espacio usado / libre / total."""
    if not HAS_PSUTIL:
        return []
    results = []
    seen = set()
    try:
        for part in psutil.disk_partitions(all=False):
            # Filtrar filesystems especiales
            if part.fstype in ("", "squashfs", "tmpfs", "devtmpfs", "overlay"):
                continue
            # Evitar duplicados por device
            if part.device in seen:
                continue
            seen.add(part.device)
            try:
                usage = psutil.disk_usage(part.mountpoint)
                results.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                })
            except (OSError, PermissionError):
                continue
    except Exception:
        pass
    # Ordenar por tamaño desc
    results.sort(key=lambda x: -x["total"])
    return results


def get_battery() -> Optional[dict]:
    """
    Info de batería si la máquina tiene una (laptops).
    Devuelve None en desktops.
    """
    if not HAS_PSUTIL:
        return None
    try:
        b = psutil.sensors_battery()
    except (AttributeError, NotImplementedError):
        return None
    if b is None:
        return None
    # secsleft puede ser POWER_TIME_UNLIMITED (-1) o POWER_TIME_UNKNOWN (-2)
    secs = b.secsleft
    if secs == psutil.POWER_TIME_UNLIMITED:
        time_left = None  # cargador enchufado
    elif secs == psutil.POWER_TIME_UNKNOWN or secs < 0:
        time_left = None
    else:
        time_left = int(secs)
    return {
        "percent": b.percent,
        "plugged": b.power_plugged,
        "seconds_left": time_left,
    }


def get_network() -> dict:
    """Tráfico de red (bytes acumulados desde arranque)."""
    if not HAS_PSUTIL:
        return {"bytes_sent": 0, "bytes_recv": 0}
    try:
        n = psutil.net_io_counters()
        return {
            "bytes_sent": n.bytes_sent,
            "bytes_recv": n.bytes_recv,
            "packets_sent": n.packets_sent,
            "packets_recv": n.packets_recv,
        }
    except Exception:
        return {"bytes_sent": 0, "bytes_recv": 0}


def get_boot_time() -> int:
    """Timestamp Unix del último boot."""
    if not HAS_PSUTIL:
        return 0
    try:
        return int(psutil.boot_time())
    except Exception:
        return 0


def get_process_count() -> int:
    if not HAS_PSUTIL:
        return 0
    try:
        return len(psutil.pids())
    except Exception:
        return 0
