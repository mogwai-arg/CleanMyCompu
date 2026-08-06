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
from pathlib import Path
from typing import List

# winreg solo existe en Windows
if sys.platform.startswith("win"):
    import winreg
else:
    winreg = None


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
            friendly = _humanize_registry_name(name, cmd)
            source = f"registry-{hive}"
            desc = f"Registro de {hive}. Se ejecuta al iniciar sesión."
            items.append({
                "path": None,   # no es archivo — es entrada de registry
                "label": name,
                "name": friendly,
                "friendly_desc": desc,
                "recommend": None,
                "reason": "",
                "enabled": True,
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

    items.sort(key=lambda x: x["name"].lower())
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
        # HKLM requiere admin — devolver False para que la UI avise
        return False


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
            return False
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
