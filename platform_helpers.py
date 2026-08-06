"""
Detección de plataforma + helpers para paths de usuario cross-platform.
Centralizado acá para no repetir en cada módulo.
"""

import os
import sys
from pathlib import Path


def is_mac() -> bool:
    return sys.platform == "darwin"


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_linux() -> bool:
    return sys.platform.startswith("linux")


HOME = Path.home()


def user_downloads() -> Path:
    """Carpeta de Descargas. Windows usa el knownfolder API si está disponible."""
    if is_windows():
        # Muchos usuarios cambian su carpeta de Downloads
        # SHGetKnownFolderPath es lo correcto en Windows Vista+
        try:
            import ctypes
            from ctypes import windll, wintypes
            _CoTaskMemFree = ctypes.windll.ole32.CoTaskMemFree
            _CoTaskMemFree.restype = None
            _CoTaskMemFree.argtypes = [ctypes.c_void_p]
            _SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
            _SHGetKnownFolderPath.argtypes = [
                ctypes.c_char_p, wintypes.DWORD, wintypes.HANDLE,
                ctypes.POINTER(ctypes.c_wchar_p),
            ]
            # FOLDERID_Downloads = {374DE290-123F-4565-9164-39C4925E467B}
            folder_id = bytes.fromhex("90E24D373F1265459164"
                                      "39C4925E467B")  # little-endian GUID
            ptr = ctypes.c_wchar_p()
            hr = _SHGetKnownFolderPath(folder_id, 0, None, ctypes.byref(ptr))
            if hr == 0:
                result = Path(ptr.value)
                _CoTaskMemFree(ptr)
                return result
        except Exception:
            pass
    return HOME / "Downloads"


def user_documents() -> Path:
    return HOME / "Documents"


def user_desktop() -> Path:
    return HOME / "Desktop"


def user_pictures() -> Path:
    return HOME / "Pictures"


def user_videos() -> Path:
    # En Windows es "Videos", en macOS "Movies"
    if is_mac():
        return HOME / "Movies"
    return HOME / "Videos"


def user_music() -> Path:
    return HOME / "Music"


def list_data_drives() -> list:
    """
    Windows: lista todas las unidades FIJAS distintas de C: (D:, E:, etc.)
    macOS/Linux: lista vacía (todo está bajo /).
    """
    if not is_windows():
        return []
    try:
        import ctypes
        import string
        drives = []
        # GetLogicalDrives devuelve un bitmask con cada letra disponible
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i, letter in enumerate(string.ascii_uppercase):
            if not (bitmask & (1 << i)):
                continue
            if letter == "C":
                continue  # C: ya se scannea via user folders
            # Verificar que sea drive fijo (no CD, no USB temporal)
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(f"{letter}:\\")
            # 3 = DRIVE_FIXED, 4 = DRIVE_REMOTE (network), otros = skip
            if drive_type == 3:
                p = Path(f"{letter}:\\")
                if p.exists():
                    drives.append(p)
        return drives
    except Exception:
        return []


def default_duplicate_roots() -> list:
    """Carpetas por default a escanear buscando duplicados."""
    roots = [user_downloads(), user_documents(), user_desktop(),
             user_pictures(), user_videos()]
    # En Windows, sumar unidades adicionales (D:, E:, etc.)
    roots.extend(list_data_drives())
    return roots


def default_large_file_roots() -> list:
    """Carpetas por default a escanear buscando archivos grandes."""
    roots = [user_downloads(), user_documents(), user_desktop(),
             user_pictures(), user_videos()]
    roots.extend(list_data_drives())
    return roots


def list_all_disks() -> list:
    """
    Todas las unidades fijas con espacio total/libre.
    Útil para el widget StorageBar en Windows para mostrar disk info agregada.
    Devuelve lista de dicts: {mount, total, used, free, label}
    """
    import shutil as _sh
    disks = []
    if is_windows():
        try:
            import ctypes
            import string
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i, letter in enumerate(string.ascii_uppercase):
                if not (bitmask & (1 << i)):
                    continue
                mount = f"{letter}:\\"
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(mount)
                if drive_type != 3:  # solo drives fijos
                    continue
                try:
                    total, used, free = _sh.disk_usage(mount)
                    disks.append({"mount": mount, "total": total,
                                  "used": used, "free": free, "label": letter})
                except OSError:
                    pass
        except Exception:
            pass
    else:
        try:
            total, used, free = _sh.disk_usage("/")
            disks.append({"mount": "/", "total": total, "used": used,
                          "free": free, "label": "/"})
        except OSError:
            pass
    return disks


def platform_display() -> str:
    """Nombre humano de la plataforma para UI."""
    if is_mac():
        return "macOS"
    if is_windows():
        return "Windows"
    if is_linux():
        return "Linux"
    return sys.platform
