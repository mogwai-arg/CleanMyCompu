"""
Notificaciones nativas de macOS.

Estrategia:
  - Primero intentamos con `terminal-notifier` (si está instalado via Homebrew).
    Es la única forma robusta de hacer que la notificación se vea como
    enviada por CleanMyCompu con su ícono, sin necesidad de PyObjC ni firmar
    la app.
  - Si no está disponible, caemos a `osascript display notification`,
    que funciona en cualquier Mac pero muestra "Script Editor" como emisor.
  - Cualquier error es silencioso — nunca queremos que la app rompa por
    una notificación.
"""

import shutil
import subprocess
from pathlib import Path


_APP_ICON = str(Path(__file__).parent / "assets" / "app_icon.png")
_TERMINAL_NOTIFIER = shutil.which("terminal-notifier")


def notify(title: str, message: str, subtitle: str = "",
           sound: bool = False) -> None:
    """
    Muestra una notificación nativa. Nunca lanza excepción.

    - title: título de la notificación (obligatorio, corto).
    - message: cuerpo (obligatorio).
    - subtitle: opcional, va entre título y mensaje.
    - sound: si True, reproduce el sonido default del sistema.
    """
    if not title or not message:
        return

    if _TERMINAL_NOTIFIER:
        _via_terminal_notifier(title, message, subtitle, sound)
    else:
        _via_osascript(title, message, subtitle, sound)


def _via_terminal_notifier(title, message, subtitle, sound):
    args = [
        _TERMINAL_NOTIFIER,
        "-title", title,
        "-message", message,
        "-sender", "com.cleanmycompu.app",  # coincide con el bundle-id del .app
    ]
    if subtitle:
        args.extend(["-subtitle", subtitle])
    if sound:
        args.extend(["-sound", "default"])
    if Path(_APP_ICON).exists():
        args.extend(["-appIcon", _APP_ICON])
    try:
        subprocess.run(args, capture_output=True, timeout=5)
    except Exception:
        pass


def _via_osascript(title, message, subtitle, sound):
    def esc(s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    parts = [f"display notification {esc(message)} with title {esc(title)}"]
    if subtitle:
        parts.append(f"subtitle {esc(subtitle)}")
    if sound:
        parts.append('sound name "default"')
    script = " ".join(parts)
    try:
        subprocess.run(["osascript", "-e", script],
                       capture_output=True, timeout=5)
    except Exception:
        pass
