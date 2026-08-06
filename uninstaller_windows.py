"""
Windows: desinstalador de apps.

Lee las 3 uninstall keys del registro:
  - HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall  (64-bit / all users)
  - HKLM\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall  (32-bit)
  - HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall  (usuario)

Cada entrada tiene campos: DisplayName, DisplayVersion, Publisher,
InstallLocation, EstimatedSize (KB), UninstallString, QuietUninstallString.

Al desinstalar, ejecutamos el UninstallString (que suele abrir el propio
uninstaller de la app). Windows Installer se encarga.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

if sys.platform.startswith("win"):
    import winreg
else:
    winreg = None


_UNINSTALL_KEYS = [
    ("HKLM", r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    ("HKLM", r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
]


def _hive(name: str):
    return {"HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKCU": winreg.HKEY_CURRENT_USER}.get(name)


def _read_all_entries() -> List[dict]:
    """Recorre las 3 uninstall keys y devuelve dicts con todos los valores."""
    if winreg is None:
        return []
    entries = []
    for hive_name, subkey in _UNINSTALL_KEYS:
        hive = _hive(hive_name)
        if hive is None:
            continue
        try:
            with winreg.OpenKey(hive, subkey) as parent:
                i = 0
                while True:
                    try:
                        child_name = winreg.EnumKey(parent, i)
                        i += 1
                    except OSError:
                        break
                    try:
                        with winreg.OpenKey(parent, child_name) as child:
                            data = {"_registry_key": child_name,
                                    "_registry_hive": hive_name,
                                    "_registry_subkey": subkey}
                            j = 0
                            while True:
                                try:
                                    n, v, _t = winreg.EnumValue(child, j)
                                    data[n] = v
                                    j += 1
                                except OSError:
                                    break
                            entries.append(data)
                    except OSError:
                        continue
        except (FileNotFoundError, OSError):
            continue
    return entries


def _last_used_from_install(entry: dict) -> Optional[float]:
    """
    Windows no expone last-used por app fácilmente. Heurística: mtime del
    InstallLocation o del propio uninstaller. No es preciso pero da orden.
    """
    for key in ("InstallLocation", "DisplayIcon", "UninstallString"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            # Extraer path del comando (quitar "..." y args)
            p = raw.strip('"').split('"')[0]
            path = Path(p)
            if not path.exists():
                continue
            return path.stat().st_mtime
        except Exception:
            continue
    return None


def _months_ago(ts: Optional[float]) -> Optional[int]:
    if ts is None:
        return None
    import time
    return int((time.time() - ts) / 86400 / 30)


def list_installed_apps() -> List[dict]:
    """
    Devuelve lista de apps del registry.
    Filtra system components, security updates, y entradas sin uninstall string.
    Formato compatible con uninstaller.list_installed_apps() de macOS.
    """
    if winreg is None:
        return []
    entries = _read_all_entries()
    apps = []
    seen = set()
    for e in entries:
        name = e.get("DisplayName", "")
        if not name:
            continue
        # Skip system stuff
        if e.get("SystemComponent") == 1:
            continue
        # Skip Windows updates (KBxxxxxx)
        if name.startswith("Update for") or name.startswith("Security Update"):
            continue
        # Necesita uninstaller
        if not e.get("UninstallString"):
            continue
        # Deduplicar
        dedupe_key = (name.lower(), e.get("DisplayVersion", ""))
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        size_kb = e.get("EstimatedSize", 0) or 0
        try:
            size = int(size_kb) * 1024
        except (ValueError, TypeError):
            size = 0

        install_path = e.get("InstallLocation") or ""
        last_used = _last_used_from_install(e)
        months = _months_ago(last_used)
        recommend = None
        reason = ""
        if months is not None and months >= 6:
            recommend = "uninstall"
            reason = f"No usada hace {months}+ meses (fecha del instalador)."

        apps.append({
            "name": name,
            "path": Path(install_path) if install_path else Path("."),
            # En Windows no hay "bundle_id" — usamos el registry key como identidad única
            "bundle_id": e.get("_registry_key", name),
            "size": size,
            "last_used": last_used,
            "months_unused": months,
            "recommend": recommend,
            "reason": reason,
            # Fields específicos de Windows
            "publisher": e.get("Publisher", ""),
            "version": e.get("DisplayVersion", ""),
            "uninstall_string": e.get("UninstallString", ""),
            "quiet_uninstall_string": e.get("QuietUninstallString", ""),
            "install_location": install_path,
        })

    # Sort: recomendados primero, después alfabético
    apps.sort(key=lambda a: (
        (0, -(a.get("months_unused") or 0), a["name"].lower())
        if a.get("recommend") == "uninstall"
        else (1, a["name"].lower())
    ))
    return apps


def is_app_running(app_name: str) -> bool:
    """Detecta si un proceso con nombre similar está corriendo."""
    try:
        import psutil
        target = app_name.lower().replace(".exe", "")
        for p in psutil.process_iter(['name']):
            try:
                pname = (p.info.get('name') or "").lower().replace(".exe", "")
                if target in pname or pname in target:
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def find_related_processes(app_name: str, bundle_id: str) -> List[dict]:
    """Wrapper alrededor de psutil para encontrar procesos relacionados."""
    procs = []
    try:
        import psutil
        target = app_name.lower().replace(".exe", "")
        for p in psutil.process_iter(['pid', 'name']):
            try:
                pname = (p.info.get('name') or "").lower().replace(".exe", "")
                if target in pname or pname in target:
                    procs.append({"pid": p.info['pid'], "name": p.info['name']})
            except Exception:
                continue
    except Exception:
        pass
    return procs


def kill_processes(pids: List[int], force: bool = False, wait_seconds: float = 0.8):
    """Cierra procesos usando psutil (equivalente a la versión Mac)."""
    import time
    try:
        import psutil
    except ImportError:
        return pids
    for pid in pids:
        try:
            p = psutil.Process(pid)
            if force:
                p.kill()
            else:
                p.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    time.sleep(wait_seconds)
    still_alive = []
    for pid in pids:
        try:
            psutil.Process(pid)
            still_alive.append(pid)
        except psutil.NoSuchProcess:
            pass
    return still_alive


def get_uninstall_targets(app: dict) -> dict:
    """
    En Windows, el "target" es principalmente el UninstallString del registry.
    No buscamos rastros manualmente porque el uninstaller nativo debería hacerlo.
    """
    return {
        "app": app,
        "app_path": app.get("path"),
        "related_paths": [],   # el uninstaller se ocupa
        "all_paths": [],
        "total_bytes": app.get("size", 0),
    }


def uninstall_app(target: dict,
                  on_progress: Optional[Callable[[str], None]] = None) -> dict:
    """
    Ejecuta el UninstallString registrado por el instalador de la app.
    Windows abre el uninstaller nativo (a veces con GUI). El usuario
    interactúa con ese diálogo directamente.

    Devuelve dict compatible con la versión Mac:
      {"freed": bytes, "failed": list, "error": str}
    """
    app = target["app"]
    cmd = app.get("uninstall_string") or ""
    if not cmd:
        return {"freed": 0, "failed": [Path(app.get("name", "?"))],
                "error": "No hay UninstallString en el registry"}

    if on_progress:
        on_progress(f"Ejecutando desinstalador de {app['name']}…")
        on_progress("Puede aparecer un cartel de Windows pidiendo confirmación.")

    try:
        # shell=True para que Windows interprete el comando como en cmd
        proc = subprocess.Popen(cmd, shell=True)
        # No usamos timeout largo — el usuario puede tardar en clickear en el uninstaller
        proc.wait(timeout=900)  # 15 min max
        if proc.returncode == 0:
            return {"freed": app.get("size", 0), "failed": [], "error": ""}
        # returncode != 0: el uninstaller puede haber sido cancelado
        return {"freed": 0, "failed": [Path(app.get("name", "?"))],
                "error": f"El uninstaller terminó con código {proc.returncode} "
                         "(usuario canceló o falló)"}
    except subprocess.TimeoutExpired:
        return {"freed": 0, "failed": [Path(app.get("name", "?"))],
                "error": "Timeout — el uninstaller no terminó en 15 minutos"}
    except Exception as e:
        return {"freed": 0, "failed": [Path(app.get("name", "?"))],
                "error": str(e)}
