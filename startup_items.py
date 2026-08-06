"""
Elementos de inicio: LaunchAgents del usuario.

Nos limitamos a ~/Library/LaunchAgents (nivel usuario, sin sudo) porque
tocar los del sistema (/Library/LaunchAgents, /Library/LaunchDaemons)
puede romper macOS y necesita autenticación.

Deshabilitar = renombrar el .plist a .plist.disabled
Habilitar    = renombrar de vuelta a .plist
Quitar       = mover a la papelera del sistema

Para cada agente, además tratamos de dar:
  - un nombre humano (no el bundle ID)
  - una descripción de qué hace al arrancar
  - una recomendación ("disable" / None) cuando sabemos que es bloatware conocido
"""

import plistlib
from pathlib import Path
from typing import List, Optional

HOME = Path.home()
LAUNCH_AGENTS_DIR = HOME / "Library" / "LaunchAgents"


# ============================================================
# Catálogo de LaunchAgents conocidos
# ============================================================
# Cada entrada: (nombre humano, descripción, recomendación, motivo)
# recomendación = "disable" cuando es seguro y aconsejable quitarlo del arranque.
# La comparación se hace por label EXACTO o por match de prefijo (ver _lookup_known).

KNOWN_AGENTS = {
    # ---- Adobe ----
    "com.adobe.AAM.Scheduler-1.0": (
        "Adobe Application Manager",
        "Verifica actualizaciones de productos Adobe en segundo plano.",
        "disable",
        "Adobe Creative Cloud ya se ocupa cuando lo abrís. Este scheduler es redundante.",
    ),
    "com.adobe.GC.Scheduler-1.0": (
        "Adobe Genuine Software",
        "Chequea licencias de productos Adobe al arrancar.",
        "disable",
        "Se dispara solo cuando abrís una app Adobe; no hace falta al inicio.",
    ),
    "com.adobe.AdobeCreativeCloud": (
        "Adobe Creative Cloud",
        "Panel de control de Adobe. Ocupa RAM aunque no lo uses.",
        "disable",
        "Podés abrirlo desde Aplicaciones cuando lo necesites.",
    ),
    "com.adobe.ccxprocess": (
        "Adobe CCX Process",
        "Proceso interno de Creative Cloud.",
        "disable",
        "Se relanza cuando abrís algo de Adobe.",
    ),
    # ---- Google ----
    "com.google.GoogleUpdater.wake": (
        "Google Software Updater",
        "Chequea actualizaciones de Chrome, Drive y otras apps de Google.",
        "disable",
        "Chrome ya se actualiza al abrirse; este wake al arranque no es necesario.",
    ),
    "com.google.keystone.agent": (
        "Google Keystone",
        "Sistema legacy de actualizaciones de Google.",
        "disable",
        "Reemplazado por Google Updater. Podés apagarlo.",
    ),
    "com.google.keystone.xpcservice": (
        "Google Keystone XPC",
        "Servicio auxiliar de actualizaciones de Google.",
        "disable",
        "",
    ),
    # ---- Microsoft ----
    "com.microsoft.update.agent": (
        "Microsoft AutoUpdate",
        "Descarga e instala updates de Office.",
        None,
        "Recomendado dejarlo si usás Office.",
    ),
    "com.microsoft.autoupdate.helper": (
        "Microsoft AutoUpdate Helper",
        "Helper del actualizador de Office.",
        "disable",
        "El scheduler principal ya se ocupa.",
    ),
    "com.microsoft.OneDriveUpdater.Standalone": (
        "OneDrive Updater",
        "Chequea updates de OneDrive.",
        "disable",
        "OneDrive puede actualizarse al abrirse.",
    ),
    "com.microsoft.teams.TeamsUpdaterDaemon": (
        "Teams Updater",
        "Actualiza Microsoft Teams.",
        "disable",
        "Teams se actualiza al abrirse.",
    ),
    # ---- Zoom ----
    "us.zoom.ZoomDaemon": (
        "Zoom Daemon",
        "Servicio de fondo de Zoom.",
        "disable",
        "Zoom arranca cuando entrás a una reunión; no hace falta al inicio.",
    ),
    "us.zoom.ZoomAutoUpdater": (
        "Zoom AutoUpdater",
        "Chequea updates de Zoom.",
        "disable",
        "Zoom se actualiza al abrirlo.",
    ),
    # ---- Dropbox / storage ----
    "com.dropbox.DropboxMacUpdate.agent": (
        "Dropbox Updater",
        "Chequea actualizaciones de Dropbox.",
        "disable",
        "Dropbox se actualiza cuando corre.",
    ),
    # ---- Spotify ----
    "com.spotify.webhelper": (
        "Spotify Web Helper",
        "Escucha comandos de Spotify Connect desde el navegador.",
        "disable",
        "Solo hace falta si usás la web player de Spotify.",
    ),
    # ---- Elgato ----
    "com.elgato.CameraHub": (
        "Elgato Camera Hub",
        "Servicio de la cámara Elgato Facecam.",
        None,
        "Necesario si usás una Elgato para streams o llamadas.",
    ),
    "com.elgato.StreamDeck": (
        "Elgato Stream Deck",
        "App del panel Stream Deck.",
        None,
        "Necesario si usás Stream Deck.",
    ),
    # ---- Audio ----
    "com.gingeraudio.groundcontrolcaster": (
        "GroundControl Caster",
        "Ruteo de audio profesional (Ginger Audio).",
        None,
        "Dejarlo si usás GroundControl.",
    ),
    # ---- Docker ----
    "com.docker.helper": (
        "Docker Desktop Helper",
        "Helper de Docker Desktop.",
        None,
        "Necesario si Docker Desktop arranca solo al inicio.",
    ),
    # ---- Slack / Discord / mensajería ----
    "com.tinyspeck.slackmacgap.helper": (
        "Slack Helper",
        "Ayudante de Slack en segundo plano.",
        None,
        "Recomendado si querés notificaciones sin abrir Slack.",
    ),
    # ---- Actualizadores genéricos ----
    "com.oracle.java.Java-Updater": (
        "Java Updater",
        "Chequea updates del runtime de Java.",
        "disable",
        "Salvo que uses Java a diario, es innecesario.",
    ),
}


# Palabras clave del label o del programa que dan pistas para agentes desconocidos.
_PROGRAM_HINTS = [
    ("updater", "Chequea si hay actualizaciones."),
    ("autoupdate", "Chequea si hay actualizaciones automáticas."),
    ("scheduler", "Ejecuta tareas programadas a intervalos."),
    ("helper", "Servicio auxiliar de la aplicación."),
    ("daemon", "Servicio en segundo plano."),
    ("notification", "Muestra notificaciones."),
    ("agent", "Agente en segundo plano."),
    ("sync", "Sincroniza datos con la nube."),
    ("monitor", "Monitorea eventos del sistema."),
]


def _humanize_label(label: str) -> str:
    """com.adobe.AAM.Scheduler-1.0 → Adobe AAM Scheduler."""
    parts = label.split(".")
    if parts and parts[0] in ("com", "org", "us", "net", "io", "app"):
        parts = parts[1:]
    words = []
    for p in parts:
        p = p.replace("-", " ").strip()
        # Cortar sufijos "1.0" que aparecen como parte del label
        if p and not p.replace(".", "").isdigit():
            words.append(p.title() if p.islower() else p)
    return " ".join(words) or label


def _describe_program(prog: str) -> str:
    if not prog:
        return "Agente en segundo plano."
    lower = prog.lower()
    for kw, desc in _PROGRAM_HINTS:
        if kw in lower:
            return desc
    return "Agente en segundo plano."


def _lookup_known(label: str):
    """Match exacto primero, luego por prefijo del bundle ID."""
    if label in KNOWN_AGENTS:
        return KNOWN_AGENTS[label]
    # Match por prefijo (para variantes: com.adobe.AAM.Scheduler-1.5)
    for known_label, info in KNOWN_AGENTS.items():
        if label.startswith(known_label.rsplit("-", 1)[0]) or known_label.startswith(label):
            return info
    return None


def _read_plist(path: Path) -> Optional[dict]:
    try:
        with open(path, "rb") as f:
            return plistlib.load(f)
    except Exception:
        return None


def list_launch_agents() -> List[dict]:
    """
    Devuelve la lista de LaunchAgents del usuario, enriquecida con:
      friendly_name, friendly_desc, recommend ("disable"|None), reason
    Ordenada: recomendados-a-desactivar primero, luego por nombre.
    """
    items: List[dict] = []
    if not LAUNCH_AGENTS_DIR.exists():
        return items
    try:
        entries = list(LAUNCH_AGENTS_DIR.iterdir())
    except OSError:
        return items

    for entry in entries:
        name = entry.name
        enabled = name.endswith(".plist")
        disabled = name.endswith(".plist.disabled")
        if not (enabled or disabled):
            continue

        data = _read_plist(entry) or {}
        label = data.get("Label") or entry.stem.replace(".plist", "")
        if not isinstance(label, str):
            label = entry.stem

        program = data.get("Program")
        if not program:
            args = data.get("ProgramArguments")
            if isinstance(args, list) and args:
                program = " ".join(str(a) for a in args)
        if not isinstance(program, str):
            program = ""

        known = _lookup_known(label)
        if known:
            friendly_name, friendly_desc, recommend, reason = known
        else:
            friendly_name = _humanize_label(label)
            friendly_desc = _describe_program(program)
            recommend = None
            reason = ""

        items.append({
            "path": entry,
            "label": label,
            "name": friendly_name,        # usado por la UI como título de la fila
            "friendly_desc": friendly_desc,
            "recommend": recommend,        # "disable" o None
            "reason": reason,
            "enabled": enabled,
            "program": program,
            "run_at_load": bool(data.get("RunAtLoad", False)),
            "keep_alive": bool(data.get("KeepAlive", False)),
        })

    # Ordenar: recomendados-a-desactivar (y activos) primero
    def sort_key(it):
        # Prioridad 0 = recomendado desactivar + activo (más urgente)
        # 1 = recomendado desactivar pero ya desactivado
        # 2 = resto
        if it["recommend"] == "disable" and it["enabled"]:
            return (0, it["name"].lower())
        if it["recommend"] == "disable":
            return (1, it["name"].lower())
        return (2, it["name"].lower())

    items.sort(key=sort_key)
    return items


def toggle_launch_agent(path: Path, enable: bool) -> Path:
    p = Path(path)
    if enable and p.name.endswith(".plist.disabled"):
        new = p.with_name(p.name[: -len(".disabled")])
        p.rename(new)
        return new
    if (not enable) and p.name.endswith(".plist"):
        new = p.with_name(p.name + ".disabled")
        p.rename(new)
        return new
    return p


def remove_launch_agent(path: Path) -> bool:
    try:
        from send2trash import send2trash
        send2trash(str(path))
        return True
    except Exception:
        try:
            Path(path).unlink()
            return True
        except OSError:
            return False
