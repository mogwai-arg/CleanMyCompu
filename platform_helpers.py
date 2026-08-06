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


def default_duplicate_roots() -> list:
    """Carpetas por default a escanear buscando duplicados."""
    return [user_downloads(), user_documents(), user_desktop(),
            user_pictures(), user_videos()]


def default_large_file_roots() -> list:
    """Carpetas por default a escanear buscando archivos grandes."""
    return [user_downloads(), user_documents(), user_desktop(),
            user_pictures(), user_videos()]


def platform_display() -> str:
    """Nombre humano de la plataforma para UI."""
    if is_mac():
        return "macOS"
    if is_windows():
        return "Windows"
    if is_linux():
        return "Linux"
    return sys.platform
