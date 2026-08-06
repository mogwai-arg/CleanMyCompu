"""
Escaneos específicos de tu carpeta Users que suelen liberar mucho espacio.
Todos son Windows-first (aunque find_old_installers/screenshots también corren en Mac).

Módulos:
  1. get_recycle_bin_info() / empty_recycle_bin()
  2. find_old_installers()  — Downloads/*.exe, .msi, .iso, .zip, .7z...
  3. find_iphone_backups()  — iTunes / Apple Devices backups
  4. find_windows_old()      — C:\\Windows.old
  5. find_crash_dumps()      — CrashDumps + WER
  6. find_old_screenshots()  — Pictures\\Screenshots antiguos
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

USERPROFILE = Path(os.environ.get("USERPROFILE", str(Path.home())))
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", ""))
APPDATA = Path(os.environ.get("APPDATA", ""))


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
    """Devuelve (bytes, num_items) de la papelera (todas las unidades)."""
    if not sys.platform.startswith("win"):
        return 0, 0
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


def empty_recycle_bin() -> bool:
    """Vacía la papelera sin confirmación de Windows, sin UI, sin sonido."""
    if not sys.platform.startswith("win"):
        return False
    import ctypes
    SHERB_NOCONFIRMATION = 0x00000001
    SHERB_NOPROGRESSUI = 0x00000002
    SHERB_NOSOUND = 0x00000004
    try:
        hr = ctypes.windll.shell32.SHEmptyRecycleBinW(
            None, None,
            SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND,
        )
        # hr == 0 → OK, hr == -2147418113 (E_UNEXPECTED) también puede ser "ya vacía"
        return hr == 0 or hr == -2147418113
    except Exception:
        return False


# ============================================================
# 2. Instaladores viejos en Downloads
# ============================================================

INSTALLER_EXTS = {
    ".exe", ".msi", ".iso", ".img", ".zip", ".7z", ".rar",
    ".dmg", ".pkg", ".deb", ".rpm",
    ".appx", ".appxbundle", ".msix", ".msixbundle",
}


def find_old_installers(min_age_days: int = 30,
                        min_size_mb: int = 5) -> List[dict]:
    """
    Instaladores y comprimidos en Downloads más viejos que N días y >= N MB.
    Ordenados por tamaño desc.
    """
    downloads_candidates = [
        USERPROFILE / "Downloads",
        USERPROFILE / "Descargas",  # locale ES
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
    if not sys.platform.startswith("win"):
        return []
    candidates = [
        APPDATA / "Apple Computer" / "MobileSync" / "Backup",
        USERPROFILE / "Apple" / "MobileSync" / "Backup",
    ]
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
    C:\\Windows.old queda cuando actualizás Windows. Sirve por 10 días para revertir.
    Después de eso, no sirve para nada (pero Windows a veces no lo borra solo).
    Típicamente 15-30 GB.
    """
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
    """Volcados de memoria de apps que crashearon + reportes WER."""
    if not sys.platform.startswith("win"):
        return []
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
    Screenshots en Pictures\\Screenshots más viejos que N días.
    Un usuario típico tiene cientos acumulados.
    """
    candidates = [
        USERPROFILE / "Pictures" / "Screenshots",
        USERPROFILE / "Imágenes" / "Capturas de pantalla",
    ]
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
                    if f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".bmp"):
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
