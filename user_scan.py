"""
Escaneos específicos de la carpeta del usuario que suelen liberar mucho espacio.
Cross-platform: Windows y macOS. Cada función detecta la plataforma y usa
paths/API apropiadas.

Módulos:
  1. get_recycle_bin_info() / empty_recycle_bin()  — Papelera / Trash
  2. find_old_installers()  — Downloads: .exe/.msi/.dmg/.pkg/.zip viejos
  3. find_iphone_backups()  — iTunes / Apple Devices backups (ambos OS)
  4. find_windows_old()      — Solo Windows: C:\\Windows.old
  5. find_crash_dumps()      — CrashDumps (Win) / DiagnosticReports (Mac)
  6. find_old_screenshots()  — Screenshots antiguos
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"

USERPROFILE = Path(os.environ.get("USERPROFILE", str(Path.home())))
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", ""))
APPDATA = Path(os.environ.get("APPDATA", ""))
HOME = Path.home()


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for root, _dirs, files in os.walk(path):
            for f in files:
                try:
                    total += (Path(root) / f).stat().st_size
                except (OSError, PermissionError):
                    continue
    except (OSError, PermissionError):
        pass
    return total


# ============================================================
# 1. Papelera de reciclaje
# ============================================================

def get_recycle_bin_info() -> Tuple[int, int]:
    """Devuelve (bytes, num_items) de la papelera / Trash."""
    if IS_WIN:
        import ctypes
        from ctypes import wintypes

        class SHQUERYRBINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("i64Size", ctypes.c_int64),
                ("i64NumItems", ctypes.c_int64),
            ]

        info = SHQUERYRBINFO()
        info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
        try:
            hr = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
            if hr == 0:
                return int(info.i64Size), int(info.i64NumItems)
        except Exception:
            pass
        return 0, 0

    if IS_MAC:
        # Trash del usuario + Trashes de discos externos montados
        total_size = 0
        total_items = 0
        trash_dirs = [HOME / ".Trash"]
        volumes = Path("/Volumes")
        if volumes.exists():
            try:
                for vol in volumes.iterdir():
                    trashes = vol / ".Trashes"
                    if trashes.exists():
                        # Cada usuario tiene una subcarpeta con su UID
                        try:
                            for user_trash in trashes.iterdir():
                                if user_trash.is_dir():
                                    trash_dirs.append(user_trash)
                        except (OSError, PermissionError):
                            pass
            except (OSError, PermissionError):
                pass

        for td in trash_dirs:
            if not td.exists():
                continue
            try:
                for entry in td.iterdir():
                    try:
                        if entry.is_dir():
                            total_size += _dir_size(entry)
                        else:
                            total_size += entry.stat().st_size
                        total_items += 1
                    except (OSError, PermissionError):
                        continue
            except (OSError, PermissionError):
                continue
        return total_size, total_items

    return 0, 0


def empty_recycle_bin() -> bool:
    """Vacía la papelera / Trash sin confirmación."""
    if IS_WIN:
        import ctypes
        SHERB_NOCONFIRMATION = 0x00000001
        SHERB_NOPROGRESSUI = 0x00000002
        SHERB_NOSOUND = 0x00000004
        try:
            hr = ctypes.windll.shell32.SHEmptyRecycleBinW(
                None, None,
                SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND,
            )
            return hr == 0 or hr == -2147418113
        except Exception:
            return False

    if IS_MAC:
        # Usamos AppleScript para que Finder vacíe la Trash "correctamente"
        # (respeta locks, permisos y demás). Si Finder no responde, borramos a mano.
        import subprocess
        try:
            r = subprocess.run(
                ["osascript", "-e", 'tell application "Finder" to empty trash'],
                capture_output=True, timeout=60,
            )
            if r.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, OSError):
            pass
        # Fallback manual
        import shutil as _sh
        ok = True
        trash_dirs = [HOME / ".Trash"]
        volumes = Path("/Volumes")
        if volumes.exists():
            try:
                for vol in volumes.iterdir():
                    trashes = vol / ".Trashes"
                    if trashes.exists():
                        try:
                            for ut in trashes.iterdir():
                                if ut.is_dir():
                                    trash_dirs.append(ut)
                        except (OSError, PermissionError):
                            pass
            except (OSError, PermissionError):
                pass
        for td in trash_dirs:
            if not td.exists():
                continue
            try:
                for entry in td.iterdir():
                    try:
                        if entry.is_dir():
                            _sh.rmtree(entry, ignore_errors=True)
                        else:
                            entry.unlink(missing_ok=True)
                    except OSError:
                        ok = False
            except OSError:
                ok = False
        return ok

    return False


# ============================================================
# 2. Instaladores viejos en Downloads
# ============================================================

INSTALLER_EXTS = {
    ".exe", ".msi", ".iso", ".img", ".zip", ".7z", ".rar",
    ".dmg", ".pkg", ".deb", ".rpm",
    ".appx", ".appxbundle", ".msix", ".msixbundle",
    ".tar", ".tar.gz", ".tgz", ".gz", ".bz2",
}


def find_old_installers(min_age_days: int = 30,
                        min_size_mb: int = 5) -> List[dict]:
    """
    Instaladores y comprimidos en Downloads más viejos que N días y >= N MB.
    Ordenados por tamaño desc.
    """
    # Home base para Downloads
    base_home = USERPROFILE if IS_WIN else HOME
    downloads_candidates = [
        base_home / "Downloads",
        base_home / "Descargas",  # locale ES
    ]
    cutoff = datetime.now() - timedelta(days=min_age_days)
    min_bytes = min_size_mb * 1024 * 1024
    results = []
    seen = set()
    for downloads in downloads_candidates:
        if not downloads.exists():
            continue
        try:
            for f in downloads.rglob("*"):
                try:
                    if not f.is_file():
                        continue
                    if f.suffix.lower() not in INSTALLER_EXTS:
                        continue
                    stat = f.stat()
                    if stat.st_size < min_bytes:
                        continue
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    if mtime > cutoff:
                        continue
                    key = str(f.resolve())
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append({
                        "path": f,
                        "size": stat.st_size,
                        "mtime": mtime,
                        "ext": f.suffix.lower(),
                    })
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            pass
    results.sort(key=lambda x: -x["size"])
    return results


# ============================================================
# 3. Backups de iPhone / iPad
# ============================================================

def find_iphone_backups() -> List[dict]:
    """
    Backups de iOS creados por iTunes o Apple Devices (UWP).
    Cada backup ocupa el snapshot completo del dispositivo — típicamente 10-50 GB.
    Borrar un backup no afecta tu iPhone (solo la copia local).
    """
    if IS_WIN:
        candidates = [
            APPDATA / "Apple Computer" / "MobileSync" / "Backup",
            USERPROFILE / "Apple" / "MobileSync" / "Backup",
        ]
    elif IS_MAC:
        candidates = [
            HOME / "Library" / "Application Support" / "MobileSync" / "Backup",
        ]
    else:
        return []
    results = []
    for base in candidates:
        if not base.exists():
            continue
        try:
            for backup_dir in base.iterdir():
                if not backup_dir.is_dir():
                    continue
                sz = _dir_size(backup_dir)
                if sz == 0:
                    continue
                try:
                    mtime = datetime.fromtimestamp(backup_dir.stat().st_mtime)
                except OSError:
                    mtime = None
                # Intentar leer Info.plist para el nombre del dispositivo
                device_name = _read_backup_device_name(backup_dir)
                results.append({
                    "path": backup_dir,
                    "size": sz,
                    "mtime": mtime,
                    "device_name": device_name,
                    "uuid": backup_dir.name,
                })
        except (OSError, PermissionError):
            pass
    results.sort(key=lambda x: -x["size"])
    return results


def _read_backup_device_name(backup_dir: Path) -> str:
    """Intenta extraer el nombre del dispositivo desde Info.plist."""
    info_plist = backup_dir / "Info.plist"
    if not info_plist.exists():
        return ""
    try:
        import plistlib
        with open(info_plist, "rb") as f:
            data = plistlib.load(f)
        return data.get("Device Name", "") or data.get("Product Name", "")
    except Exception:
        return ""


# ============================================================
# 4. Windows.old (upgrade anterior)
# ============================================================

def find_windows_old() -> Optional[dict]:
    """
    C:\\Windows.old queda cuando actualizás Windows. Sólo Windows.
    """
    if not IS_WIN:
        return None
    p = Path(r"C:\Windows.old")
    if not p.exists():
        return None
    sz = _dir_size(p)
    if sz == 0:
        return None
    return {
        "path": p,
        "size": sz,
    }


# ============================================================
# 5. Crash dumps + Windows Error Reporting
# ============================================================

def find_crash_dumps() -> List[dict]:
    """Volcados de memoria de apps que crashearon."""
    if IS_WIN:
        candidates = [
            (LOCALAPPDATA / "CrashDumps",
             "Crash dumps de aplicaciones",
             "Volcados de memoria de programas que crashearon. Sólo sirven para debug."),
            (LOCALAPPDATA / "Microsoft" / "Windows" / "WER" / "ReportArchive",
             "Windows Error Reporting — archivados",
             "Reportes de errores archivados que Windows envía a Microsoft."),
            (LOCALAPPDATA / "Microsoft" / "Windows" / "WER" / "ReportQueue",
             "Windows Error Reporting — cola",
             "Reportes de errores pendientes de enviar."),
            (LOCALAPPDATA / "Microsoft" / "Windows" / "WER" / "Temp",
             "Windows Error Reporting — temporales",
             "Archivos temporales de reportes."),
        ]
    elif IS_MAC:
        candidates = [
            (HOME / "Library" / "Logs" / "DiagnosticReports",
             "Reportes de crashes de apps (usuario)",
             "Volcados de apps que crashearon. Sólo sirven para debug."),
            (HOME / "Library" / "Application Support" / "CrashReporter",
             "CrashReporter (usuario)",
             "Cache del reportador de crashes de macOS."),
            (Path("/Library/Logs/DiagnosticReports"),
             "Reportes de crashes de sistema",
             "Volcados de procesos del sistema. Necesita admin para borrar."),
        ]
    else:
        return []
    results = []
    for path, name, desc in candidates:
        if path.exists():
            sz = _dir_size(path)
            if sz > 0:
                results.append({
                    "path": path,
                    "size": sz,
                    "name": name,
                    "desc": desc,
                })
    return results


# ============================================================
# 6. Screenshots antiguos
# ============================================================

def find_old_screenshots(min_age_days: int = 90,
                         min_size_kb: int = 50) -> List[dict]:
    """
    Screenshots más viejos que N días. Un usuario típico tiene cientos acumulados.
    Windows: carpeta Screenshots. Mac: Desktop (default) o donde el user haya cambiado.
    """
    if IS_WIN:
        candidates = [
            USERPROFILE / "Pictures" / "Screenshots",
            USERPROFILE / "Imágenes" / "Capturas de pantalla",
            USERPROFILE / "OneDrive" / "Pictures" / "Screenshots",
        ]
        # Mac usa "Screen Shot ...png" o "Captura de pantalla ...png"
        name_filter = None
    elif IS_MAC:
        # macOS por default guarda screenshots en Desktop con nombre que empieza con
        # "Screen Shot" (en) o "Captura de pantalla" (es) o "Screenshot" (13+)
        candidates = [
            HOME / "Desktop",
            HOME / "Pictures" / "Screenshots",
            HOME / "Documents" / "Screenshots",
        ]
        # Filtrar por nombre en Desktop para no borrar cualquier PNG del user
        name_filter = ("screen shot", "screenshot", "captura de pantalla")
    else:
        return []

    cutoff = datetime.now() - timedelta(days=min_age_days)
    min_bytes = min_size_kb * 1024
    results = []
    for ss_dir in candidates:
        if not ss_dir.exists():
            continue
        try:
            for f in ss_dir.iterdir():
                try:
                    if not f.is_file():
                        continue
                    if f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".bmp", ".heic"):
                        continue
                    # En Mac's Desktop solo tomamos archivos que parecen screenshots
                    if name_filter is not None:
                        name_low = f.name.lower()
                        if not any(name_low.startswith(p) for p in name_filter):
                            continue
                    stat = f.stat()
                    if stat.st_size < min_bytes:
                        continue
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    if mtime > cutoff:
                        continue
                    results.append({
                        "path": f,
                        "size": stat.st_size,
                        "mtime": mtime,
                    })
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            pass
    results.sort(key=lambda x: -x["size"])
    return results


# ============================================================
# Función principal de escaneo — corre todo
# ============================================================

def scan_all(on_progress=None) -> dict:
    """
    Corre todos los escaneos. Devuelve dict con las 6 secciones.
    on_progress(str) callback opcional para mostrar en UI.
    """
    def _p(msg):
        if on_progress:
            on_progress(msg)

    _p("Consultando papelera de reciclaje…")
    bin_size, bin_items = get_recycle_bin_info()

    _p("Buscando instaladores viejos en Descargas…")
    installers = find_old_installers()

    _p("Buscando backups de iPhone/iPad…")
    iphone = find_iphone_backups()

    _p("Chequeando Windows.old…")
    win_old = find_windows_old()

    _p("Buscando crash dumps y WER…")
    dumps = find_crash_dumps()

    _p("Buscando screenshots antiguos…")
    screenshots = find_old_screenshots()

    return {
        "recycle_bin": {"size": bin_size, "items": bin_items},
        "installers": installers,
        "iphone_backups": iphone,
        "windows_old": win_old,
        "crash_dumps": dumps,
        "screenshots": screenshots,
    }
