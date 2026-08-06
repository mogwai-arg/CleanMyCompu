"""
Memory Clean para macOS.

Usa el comando nativo `purge` (viene con macOS) para liberar páginas de memoria
que estaban en cache pero ya no se están usando (Pages inactive / compressed).

`purge` requiere permisos de admin desde macOS 10.9+, así que lo lanzamos via
osascript para que macOS pida la contraseña con su diálogo nativo.
"""

import subprocess
from typing import Callable, Optional


def get_memory_stats() -> dict:
    """
    Combina `sysctl hw.memsize` (total) con `vm_stat` (uso).
    Devuelve dict con bytes:
      total, used, free, inactive, active, wired, compressed
    """
    total = 0
    try:
        total = int(subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True, text=True, timeout=3,
        ).stdout.strip())
    except Exception:
        pass

    page_size = 16384  # macOS Apple Silicon default
    stats = {}
    try:
        out = subprocess.run(
            ["vm_stat"], capture_output=True, text=True, timeout=3,
        ).stdout
        for line in out.splitlines():
            if "page size of" in line:
                try:
                    page_size = int(line.split("of", 1)[1].split("bytes")[0].strip())
                except Exception:
                    pass
                continue
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            val = val.strip().rstrip(".")
            if val.isdigit():
                stats[key.strip()] = int(val) * page_size
    except Exception:
        return {"total": total, "used": 0, "free": 0, "inactive": 0,
                "active": 0, "wired": 0, "compressed": 0}

    free = stats.get("Pages free", 0)
    inactive = stats.get("Pages inactive", 0)
    active = stats.get("Pages active", 0)
    wired = stats.get("Pages wired down", 0)
    compressed = stats.get("Pages occupied by compressor", 0)
    # macOS considera "usada" = active + wired + compressed
    used = active + wired + compressed
    return {
        "total": total, "used": used, "free": free,
        "inactive": inactive, "active": active,
        "wired": wired, "compressed": compressed,
    }


def free_memory(on_status: Optional[Callable[[str], None]] = None) -> dict:
    """
    Ejecuta `purge` con permisos de admin (macOS pide contraseña).

    Devuelve dict:
      {"before": stats, "after": stats, "freed": bytes,
       "cancelled": bool (opcional), "error": str (opcional)}
    """
    before = get_memory_stats()
    if on_status:
        on_status("Liberando memoria inactiva…")

    apple_script = ('do shell script "/usr/sbin/purge" '
                    'with administrator privileges')
    try:
        result = subprocess.run(
            ["osascript", "-e", apple_script],
            capture_output=True, text=True, timeout=60,
        )
    except Exception as e:
        return {"before": before, "after": before, "freed": 0, "error": str(e)}

    if result.returncode != 0:
        err = (result.stderr or "").strip()
        if "-128" in err or "canceled" in err.lower() or "cancelled" in err.lower():
            return {"before": before, "after": before, "freed": 0, "cancelled": True}
        return {"before": before, "after": before, "freed": 0, "error": err}

    after = get_memory_stats()
    # "Freed" = cuánto creció la RAM libre (aprox — el kernel también reasigna)
    freed = after["free"] - before["free"]
    return {"before": before, "after": after, "freed": max(0, freed)}
