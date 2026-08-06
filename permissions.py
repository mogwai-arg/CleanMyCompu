"""
Helpers para gestionar los permisos de macOS (TCC).

macOS pregunta al usuario cada vez que una app quiere acceder a carpetas
protegidas (Downloads, Documents, Desktop, Movies, Pictures, Removable
volumes, etc.). Esas preguntas se vuelven una plaga si escaneás mucho.

La solución es darle "Acceso completo al disco" a la app una única vez —
después macOS no vuelve a preguntar. Este módulo abre el panel exacto
de Preferencias del Sistema para hacerlo con un clic.
"""

import subprocess
import sys


# URLs de "anchor" del prefs pane de macOS
_URL_FULL_DISK_ACCESS = "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"
_URL_FILES_AND_FOLDERS = "x-apple.systempreferences:com.apple.preference.security?Privacy_FilesAndFolders"
_URL_AUTOMATION = "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation"


def open_full_disk_access():
    """Abre Preferencias del Sistema → Privacidad y Seguridad → Acceso completo al disco."""
    _open_url(_URL_FULL_DISK_ACCESS)


def open_files_and_folders():
    """Abre el panel de permisos por carpeta (Downloads, Documents, etc.)."""
    _open_url(_URL_FILES_AND_FOLDERS)


def _open_url(url: str):
    if sys.platform != "darwin":
        return
    try:
        subprocess.run(["open", url], check=False, timeout=5)
    except Exception:
        pass
