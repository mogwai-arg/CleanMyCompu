"""
Windows: elementos de inicio.

Lee 3 fuentes que Windows usa para arrancar programas al inicio:
  1. Registry HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run  (usuario)
  2. Registry HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run  (todos)
  3. Carpeta %APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup

No tocamos Task Scheduler acá (más complejo, próxima ronda).
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

# winreg solo existe en Windows
if sys.platform.startswith("win"):
    import winreg
else:
    winreg = None


# ============================================================
# Catálogo de bloatware conocido en Windows
# ============================================================
# Cada entrada: (nombre humano, descripción, recomendación, motivo)
# recomendación = "disable" (bloatware seguro) | "remove" (quitar directamente) | None
# Match por prefijo/substring case-insensitive del nombre en registry.
KNOWN_STARTUP_WIN: List[Tuple[str, str, str, Optional[str], str]] = [
    # match_pattern, friendly_name, friendly_desc, recommend, reason
    ("AdobeAAMUpdater", "Adobe Application Manager Updater",
     "Chequea updates de productos Adobe en el arranque.",
     "disable",
     "Adobe Creative Cloud ya se encarga cuando lo abrís; este updater al inicio es redundante."),
    ("AdobeGCInvoker", "Adobe Genuine Software",
     "Verifica licencias de productos Adobe.",
     "disable",
     "Se dispara solo cuando abrís una app Adobe; no hace falta al arranque."),
    ("Adobe Creative Cloud", "Adobe Creative Cloud",
     "Panel de Creative Cloud. Ocupa RAM y CPU aun sin usar.",
     "disable",
     "Podés abrirlo cuando lo necesites desde el menú Inicio."),
    ("AdobeUpdater", "Adobe Updater",
     "Otro updater residual de Adobe.",
     "disable",
     "Redundante con Creative Cloud."),
    ("CCXProcess", "Adobe CCX Process",
     "Proceso auxiliar de Creative Cloud.",
     "disable",
     "Se relanza cuando abrís algo de Adobe."),
    ("HPNotifications", "HP Notifications",
     "Notificaciones de HP (soporte, promos, ofertas).",
     "disable",
     "Bloatware típico de HP. Podés apagarlo sin miedo."),
    ("HPSupportAssistant", "HP Support Assistant",
     "Asistente de soporte HP en segundo plano.",
     "disable",
     "Sólo se necesita cuando tenés un problema; podés abrirlo manualmente."),
    ("HP System Event", "HP System Event Utility",
     "Detecta eventos de hardware HP (teclas especiales, etc.).",
     None,
     "Puede afectar teclas de función del portátil. Solo apagalo si sabés lo que hacés."),
    ("HotKeyServiceUWP", "HP HotKey Service",
     "Gestiona teclas de función Fn del portátil HP.",
     None,
     "Puede afectar teclas Fn / brillo / volumen."),
    ("MicrosoftEdgeAutoLaunch", "Microsoft Edge (autolanzar)",
     "Edge se lanza solo al iniciar sesión.",
     "disable",
     "Innecesario y consume RAM; podés abrir Edge cuando quieras."),
    ("OneDrive", "Microsoft OneDrive",
     "Sincroniza tus archivos con OneDrive.",
     None,
     "Si usás OneDrive, dejalo. Si no, podés quitarlo."),
    ("Skype", "Skype",
     "Skype se lanza al iniciar sesión.",
     "disable",
     "Podés abrirlo cuando lo necesites."),
    ("Teams", "Microsoft Teams",
     "Teams se lanza al iniciar sesión.",
     "disable",
     "Podés abrirlo cuando lo necesites. Ahorra RAM al arranque."),
    ("Spotify", "Spotify",
     "Spotify se abre al iniciar sesión.",
     "disable",
     "Podés abrirlo cuando quieras escuchar música."),
    ("Discord", "Discord",
     "Discord se abre al iniciar sesión.",
     "disable",
     "Podés abrirlo cuando lo necesites."),
    ("Steam", "Steam",
     "Steam se abre al iniciar sesión.",
     "disable",
     "Podés abrirlo cuando quieras jugar."),
    ("EpicGamesLauncher", "Epic Games Launcher",
     "Epic Games se abre al iniciar sesión.",
     "disable",
     "Podés abrirlo cuando quieras jugar."),
    ("iTunesHelper", "iTunes Helper",
     "Helper de iTunes al arranque.",
     "disable",
     "Sólo se necesita cuando conectás un iPhone/iPod."),
    ("QuickTime", "QuickTime Task",
     "Verifica updates de QuickTime.",
     "disable",
     "QuickTime está descontinuado en Windows; podés quitarlo."),
    ("SunJavaUpdateSched", "Java Update Scheduler",
     "Verifica updates de Java.",
     "disable",
     "Java se actualiza al abrirse; el scheduler es redundante."),
    ("RtkAudUService", "Realtek Audio Service",
     "Servicio de audio Realtek.",
     None,
     "Necesario para el audio del sistema. NO desactivar."),
    ("SecurityHealth", "Windows Security",
     "Ícono de seguridad de Windows Defender.",
     None,
     "Sistema — dejar activo."),
    ("Dropbox", "Dropbox",
     "Sincroniza tus archivos con Dropbox.",
     None,
     "Si usás Dropbox, dejalo."),
    ("GoogleDrive", "Google Drive",
     "Sincroniza tus archivos con Google Drive.",
     None,
     "Si usás Drive, dejalo."),
    ("GoogleUpdater", "Google Updater",
     "Chequea updates de Chrome, Drive y otras apps Google.",
     "disable",
     "Chrome ya se actualiza al abrirse. Podés apagarlo."),
    ("Nahimic", "Nahimic Audio",
     "Software de audio Nahimic (portátiles gaming).",
     "disable",
     "Sólo aporta EQ; podés apagarlo si no lo usás."),
    ("Cortana", "Cortana",
     "Asistente Cortana al arranque.",
     "disable",
     "Poco útil. Podés desactivar sin perder nada."),
    ("Zoom", "Zoom",
     "Zoom se abre al iniciar sesión.",
     "disable",
     "Podés abrirlo cuando tengas una reunión."),
    ("Slack", "Slack",
     "Slack se abre al iniciar sesión.",
     "disable",
     "Podés abrirlo cuando lo necesites."),
    ("CCleaner", "CCleaner",
     "CCleaner en segundo plano.",
     "disable",
     "No hace falta al arranque; podés abrirlo cuando quieras limpiar."),
    ("EaseUS", "EaseUS Agent",
     "Agente de EaseUS.",
     "disable",
     "Podés abrir EaseUS cuando lo necesites."),
    ("iCUE", "Corsair iCUE",
     "Software de periféricos Corsair.",
     None,
     "Si usás periféricos Corsair con perfiles, dejalo."),
    ("Razer", "Razer Central",
     "Software de periféricos Razer.",
     None,
     "Si usás periféricos Razer con perfiles, dejalo."),
    ("Logi", "Logitech Options / G HUB",
     "Software de periféricos Logitech.",
     None,
     "Si usás periféricos Logitech con perfiles, dejalo."),
]


def _lookup_known_win(reg_name: str, cmd: str) -> Optional[Tuple[str, str, Optional[str], str]]:
    """Busca en el catálogo por prefijo/substring case-insensitive."""
    name_low = reg_name.lower()
    cmd_low = cmd.lower()
    for match, friendly, desc, recommend, reason in KNOWN_STARTUP_WIN:
        m = match.lower()
        if name_low.startswith(m) or m in name_low or m in cmd_low:
            return (friendly, desc, recommend, reason)
    return None


_RUN_KEYS = [
    (r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
    (r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
    # 32-bit apps en Windows de 64-bit
    (r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
]


def _startup_folder() -> Path:
    """Carpeta Startup del usuario."""
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return Path()
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _read_registry_key(hive_name: str, subkey: str) -> list:
    """Devuelve lista de (name, value) del registry hive."""
    if winreg is None:
        return []
    hive = {"HKCU": winreg.HKEY_CURRENT_USER,
            "HKLM": winreg.HKEY_LOCAL_MACHINE}.get(hive_name)
    if hive is None:
        return []
    entries = []
    try:
        with winreg.OpenKey(hive, subkey) as key:
            i = 0
            while True:
                try:
                    name, value, _type = winreg.EnumValue(key, i)
                    entries.append((name, str(value)))
                    i += 1
                except OSError:
                    break
    except (FileNotFoundError, OSError):
        pass
    return entries


def _humanize_registry_name(name: str, cmd: str) -> str:
    """Nombre legible: prioriza el 'name' del registry, si es raro cae al basename del exe."""
    if name and not name.startswith("{"):
        return name
    # Extraer el primer .exe del cmd
    parts = cmd.replace('"', "").split()
    for p in parts:
        if p.lower().endswith(".exe"):
            return Path(p).stem
    return name or "?"


def list_startup() -> List[dict]:
    """
    Devuelve lista unificada de elementos de inicio en Windows.
    Formato compatible con startup_items.list_launch_agents():
      { "path": Path or None, "label": str, "name": str,
        "friendly_desc": str, "recommend": None, "reason": str,
        "enabled": True, "program": str,
        "run_at_load": True, "keep_alive": False,
        "source": "registry-HKCU" | "registry-HKLM" | "startup-folder" }
    """
    items: List[dict] = []

    # 1) Registry Run keys
    for subkey, hive in _RUN_KEYS:
        for name, cmd in _read_registry_key(hive, subkey):
            # Detectar si está deshabilitado por convención (sufijo .disabled)
            is_disabled = name.endswith(".disabled")
            real_name = name[:-len(".disabled")] if is_disabled else name
            friendly = _humanize_registry_name(real_name, cmd)
            source = f"registry-{hive}"

            known = _lookup_known_win(real_name, cmd)
            if known:
                friendly_name, friendly_desc_extra, recommend, reason = known
                desc = f"{friendly_desc_extra} · Registro de {hive}."
                friendly = friendly_name
            else:
                desc = f"Registro de {hive}. Se ejecuta al iniciar sesión."
                recommend = None
                reason = ""

            items.append({
                "path": None,   # no es archivo — es entrada de registry
                "label": name,
                "name": friendly,
                "friendly_desc": desc,
                "recommend": recommend,
                "reason": reason,
                "enabled": not is_disabled,
                "program": cmd,
                "run_at_load": True,
                "keep_alive": False,
                "source": source,
                "registry_hive": hive,
                "registry_subkey": subkey,
                "registry_value": name,
            })

    # 2) Carpeta Startup del usuario
    folder = _startup_folder()
    if folder.exists():
        try:
            for entry in folder.iterdir():
                if entry.is_file() and entry.suffix.lower() in (".lnk", ".exe", ".bat", ".cmd"):
                    items.append({
                        "path": entry,
                        "label": entry.stem,
                        "name": entry.stem,
                        "friendly_desc": f"Acceso directo en la carpeta Startup del usuario.",
                        "recommend": None,
                        "reason": "",
                        "enabled": True,
                        "program": str(entry),
                        "run_at_load": True,
                        "keep_alive": False,
                        "source": "startup-folder",
                    })
        except OSError:
            pass

    # Ordenar: bloatware recomendado desactivar y activo primero, luego resto
    def sort_key(it):
        if it["recommend"] == "disable" and it["enabled"]:
            return (0, it["name"].lower())
        if it["recommend"] == "disable":
            return (1, it["name"].lower())
        return (2, it["name"].lower())

    items.sort(key=sort_key)
    return items


def toggle(item: dict, enable: bool) -> bool:
    """
    Habilitar/deshabilitar un item de inicio.
    Para registry: renombra el valor agregando/quitando ".disabled" al nombre.
    Para carpeta Startup: renombra el archivo agregando/quitando ".disabled".
    """
    if winreg is None:
        return False

    source = item.get("source", "")
    if source.startswith("registry"):
        return _toggle_registry(item, enable)
    if source == "startup-folder":
        return _toggle_file(item, enable)
    return False


def _toggle_registry(item: dict, enable: bool) -> bool:
    """
    Estrategia: renombramos el valor en registry a NAME.disabled cuando se deshabilita.
    Windows ignora valores que no matcheen el nombre exacto esperado.
    """
    hive = {"HKCU": winreg.HKEY_CURRENT_USER,
            "HKLM": winreg.HKEY_LOCAL_MACHINE}.get(item.get("registry_hive", ""))
    if hive is None:
        return False
    subkey = item["registry_subkey"]
    old_name = item["registry_value"]
    new_name = old_name[:-len(".disabled")] if enable and old_name.endswith(".disabled") \
               else (old_name if enable else old_name + ".disabled")
    if new_name == old_name:
        return True  # nada que hacer
    try:
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
            # Leer valor + tipo
            value, vtype = winreg.QueryValueEx(key, old_name)
            # Crear el nuevo, borrar el viejo
            winreg.SetValueEx(key, new_name, 0, vtype, value)
            winreg.DeleteValue(key, old_name)
        return True
    except (PermissionError, OSError):
        # HKLM requiere admin → escalar via UAC (PowerShell RunAs)
        return _elevated_registry_rename(
            item.get("registry_hive", ""), subkey, old_name, new_name
        )


def _toggle_file(item: dict, enable: bool) -> bool:
    """Startup folder: renombrar el .lnk agregando .disabled al final."""
    p = Path(item["path"])
    if enable and p.name.endswith(".disabled"):
        new = p.with_name(p.name[: -len(".disabled")])
        p.rename(new)
    elif (not enable) and not p.name.endswith(".disabled"):
        new = p.with_name(p.name + ".disabled")
        p.rename(new)
    return True


def remove(item: dict) -> bool:
    """Quitar completamente el item de inicio."""
    if winreg is None:
        return False
    source = item.get("source", "")
    if source.startswith("registry"):
        hive = {"HKCU": winreg.HKEY_CURRENT_USER,
                "HKLM": winreg.HKEY_LOCAL_MACHINE}.get(item.get("registry_hive", ""))
        if hive is None:
            return False
        try:
            with winreg.OpenKey(hive, item["registry_subkey"], 0, winreg.KEY_ALL_ACCESS) as key:
                winreg.DeleteValue(key, item["registry_value"])
            return True
        except (PermissionError, OSError):
            # HKLM requiere admin → escalar via UAC
            return _elevated_registry_delete(
                item.get("registry_hive", ""),
                item["registry_subkey"],
                item["registry_value"],
            )
    if source == "startup-folder":
        try:
            from send2trash import send2trash
            send2trash(str(item["path"]))
            return True
        except Exception:
            try:
                Path(item["path"]).unlink()
                return True
            except OSError:
                return False
    return False


# ============================================================
# Elevación UAC via PowerShell RunAs
# ============================================================
# Cuando HKLM devuelve PermissionError, escribimos un script .ps1 temporal
# y lo lanzamos con Start-Process -Verb RunAs (dispara el prompt UAC).
# El usuario ve UNA sola ventana UAC y no tenemos que reiniciar la app como admin.

def _run_elevated_ps(script: str, timeout: int = 60) -> bool:
    """Ejecuta un script PowerShell con UAC. Devuelve True si exit code = 0."""
    if not sys.platform.startswith("win"):
        return False
    fd, script_path = tempfile.mkstemp(suffix=".ps1", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig") as f:  # BOM para PS
            f.write(script)
            # Al final: forzar exit code 0/1 segun errores
            f.write("\nif ($?) { exit 0 } else { exit 1 }\n")
        # Start-Process con -Wait espera a que termine y -PassThru + -Verb RunAs dispara UAC.
        # Redirigimos stdout/stderr a null (WindowStyle Hidden).
        outer = (
            f"$p = Start-Process powershell -Verb RunAs -Wait -PassThru "
            f"-WindowStyle Hidden -ArgumentList "
            f"'-NoProfile','-ExecutionPolicy','Bypass','-File','{script_path}'; "
            f"exit $p.ExitCode"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", outer],
            capture_output=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False
    finally:
        try:
            Path(script_path).unlink()
        except OSError:
            pass


def _ps_hive(hive: str) -> str:
    return "HKLM:" if hive == "HKLM" else "HKCU:"


def _ps_escape(s: str) -> str:
    """Escapa string para PowerShell literal simple-quoted."""
    return s.replace("'", "''")


def _elevated_registry_rename(hive: str, subkey: str, old_name: str, new_name: str) -> bool:
    """Renombra un valor de registry con elevación UAC."""
    if hive not in ("HKCU", "HKLM"):
        return False
    reg_path = f"{_ps_hive(hive)}\\{subkey}"
    old_e = _ps_escape(old_name)
    new_e = _ps_escape(new_name)
    path_e = _ps_escape(reg_path)
    script = (
        f"$item = Get-ItemProperty -LiteralPath '{path_e}' -Name '{old_e}' -ErrorAction Stop;\n"
        f"$val = $item.'{old_e}';\n"
        f"Set-ItemProperty -LiteralPath '{path_e}' -Name '{new_e}' -Value $val -ErrorAction Stop;\n"
        f"Remove-ItemProperty -LiteralPath '{path_e}' -Name '{old_e}' -Force -ErrorAction Stop;\n"
    )
    return _run_elevated_ps(script)


def _elevated_registry_delete(hive: str, subkey: str, value_name: str) -> bool:
    """Borra un valor de registry con elevación UAC."""
    if hive not in ("HKCU", "HKLM"):
        return False
    reg_path = f"{_ps_hive(hive)}\\{subkey}"
    name_e = _ps_escape(value_name)
    path_e = _ps_escape(reg_path)
    script = (
        f"Remove-ItemProperty -LiteralPath '{path_e}' -Name '{name_e}' "
        f"-Force -ErrorAction Stop;\n"
    )
    return _run_elevated_ps(script)
