"""
Módulo de rendimiento — lista procesos por uso de RAM y permite
suspenderlos / reanudarlos para liberar memoria virtual.

Cross-platform gracias a `psutil`:
  - Windows: process.suspend() usa SuspendThread nativo
  - macOS: process.suspend() envía SIGSTOP
  - Linux: idem SIGSTOP

Suspender NO cierra la app — sus datos siguen en memoria pero el kernel
lo puede swap a disco y libera páginas activas. Perfecto para "recuperar"
una PC que se quedó sin memoria virtual.

Al hacer `resume()` la app vuelve a correr donde quedó, sin perder trabajo.
"""

import os
import sys
from typing import List, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


# PIDs del sistema que NUNCA se pueden suspender (romperían el SO)
_PROTECTED_NAMES = {
    # macOS
    "kernel_task", "launchd", "WindowServer", "loginwindow", "Finder",
    "SystemUIServer", "Dock", "Spotlight", "Notification Center",
    "coreaudiod", "cfprefsd", "mds", "mdworker", "syncdefaultsd",
    # Windows
    "System", "Registry", "smss.exe", "csrss.exe", "wininit.exe",
    "services.exe", "lsass.exe", "svchost.exe", "explorer.exe",
    "dwm.exe", "winlogon.exe", "MemCompression",
    # Cross
    "python", "python3", "python.exe", "Python", "CleanMyCompu",
}


def is_available() -> bool:
    return HAS_PSUTIL


def _is_protected(name: str) -> bool:
    if not name:
        return True
    lname = name.lower()
    for prot in _PROTECTED_NAMES:
        if prot.lower() in lname:
            return True
    return False


def get_memory_info() -> dict:
    """
    Info de memoria del sistema. Devuelve bytes.
    Compatible con memory_clean.get_memory_stats() para reutilizar la UI.
    """
    if not HAS_PSUTIL:
        return {"total": 0, "used": 0, "free": 0, "inactive": 0,
                "active": 0, "wired": 0, "compressed": 0}
    vm = psutil.virtual_memory()
    return {
        "total": vm.total,
        "used": vm.used,
        "free": vm.available,
        # Estimaciones — psutil expone lo que puede en cada plataforma
        "inactive": getattr(vm, "inactive", 0) or 0,
        "active": getattr(vm, "active", 0) or vm.used,
        "wired": getattr(vm, "wired", 0) or 0,
        "compressed": 0,
        "percent": vm.percent,
    }


def list_processes(min_memory_mb: int = 30, include_protected: bool = False) -> List[dict]:
    """
    Lista procesos con >min_memory_mb de RAM, ordenados desc por uso.
    Excluye procesos críticos del sistema por default.

    Cada item: {pid, name, memory_mb, cpu_pct, status, is_suspended, protected}
    """
    if not HAS_PSUTIL:
        return []
    my_pid = os.getpid()
    results = []
    # Primer pass para inicializar cpu_percent()
    for p in psutil.process_iter(['pid', 'name']):
        try:
            p.cpu_percent(None)
        except Exception:
            pass

    for p in psutil.process_iter(['pid', 'name', 'memory_info', 'status', 'username']):
        try:
            info = p.info
            pid = info['pid']
            if pid == my_pid or pid == 0:
                continue
            name = info.get('name') or "?"
            protected = _is_protected(name)
            if protected and not include_protected:
                continue
            mem = info.get('memory_info')
            memory_mb = (mem.rss if mem else 0) / 1024 / 1024
            if memory_mb < min_memory_mb:
                continue
            status = info.get('status', 'unknown')
            try:
                cpu_pct = p.cpu_percent(None)
            except Exception:
                cpu_pct = 0.0
            results.append({
                'pid': pid,
                'name': name,
                'memory_mb': memory_mb,
                'cpu_pct': cpu_pct,
                'status': status,
                'is_suspended': status == psutil.STATUS_STOPPED,
                'protected': protected,
                'user': info.get('username', ''),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            continue
    results.sort(key=lambda x: -x['memory_mb'])
    return results


def suspend(pid: int) -> bool:
    """Suspender un proceso. Devuelve True si tuvo éxito."""
    if not HAS_PSUTIL:
        return False
    try:
        p = psutil.Process(pid)
        if _is_protected(p.name() or ""):
            return False
        p.suspend()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
        return False


def resume(pid: int) -> bool:
    """Reanudar un proceso suspendido."""
    if not HAS_PSUTIL:
        return False
    try:
        p = psutil.Process(pid)
        p.resume()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
        return False


def kill(pid: int) -> bool:
    """Cerrar (terminate) un proceso. Más agresivo que suspender."""
    if not HAS_PSUTIL:
        return False
    try:
        p = psutil.Process(pid)
        if _is_protected(p.name() or ""):
            return False
        p.terminate()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
        return False


def total_memory_used_by_processes(processes: List[dict]) -> float:
    """Suma la RAM (en MB) de una lista de procesos (grupos o individuales)."""
    return sum(p.get('memory_mb', 0) for p in processes)


def list_processes_grouped(min_memory_mb: int = 50) -> List[dict]:
    """
    Agrupa procesos por nombre y suma su memoria. Ideal para apps que
    tienen MUCHOS subprocesos (Chrome, Dropbox, VS Code, Slack — cada
    pestaña/ventana suele ser un proceso separado).

    Devuelve: [{name, count, memory_mb, cpu_pct, pids, any_suspended, all_suspended}]
    ordenado por memory desc.
    """
    if not HAS_PSUTIL:
        return []
    raw = list_processes(min_memory_mb=1)   # traer todos, agrupar después
    groups: dict = {}
    for p in raw:
        name = p["name"] or "?"
        # Normalizar: quitar .exe en Windows para que "chrome" y "chrome.exe" agrupen
        key = name.lower().replace(".exe", "")
        if key not in groups:
            groups[key] = {
                "name": name.replace(".exe", "") if name.endswith(".exe") else name,
                "count": 0,
                "memory_mb": 0.0,
                "cpu_pct": 0.0,
                "pids": [],
                "any_suspended": False,
                "all_suspended": True,
                "protected": p.get("protected", False),
            }
        g = groups[key]
        g["count"] += 1
        g["memory_mb"] += p["memory_mb"]
        g["cpu_pct"] += p.get("cpu_pct", 0)
        g["pids"].append(p["pid"])
        if p.get("is_suspended"):
            g["any_suspended"] = True
        else:
            g["all_suspended"] = False

    # Filtrar y ordenar
    results = [g for g in groups.values() if g["memory_mb"] >= min_memory_mb]
    results.sort(key=lambda x: -x["memory_mb"])
    return results


def suspend_all(pids: List[int]) -> int:
    """Suspende una lista de PIDs. Devuelve cuántos tuvo éxito."""
    return sum(1 for pid in pids if suspend(pid))


def resume_all(pids: List[int]) -> int:
    """Reanuda una lista de PIDs. Devuelve cuántos tuvo éxito."""
    return sum(1 for pid in pids if resume(pid))


def kill_all(pids: List[int]) -> int:
    """Cierra una lista de PIDs. Devuelve cuántos tuvo éxito."""
    return sum(1 for pid in pids if kill(pid))
