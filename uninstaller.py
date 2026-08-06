"""
Desinstalador de apps.

Para cada .app instalada:
  1. Lee su CFBundleIdentifier del Info.plist.
  2. Busca archivos relacionados en ~/Library usando el bundle ID
     (Preferences, Caches, Application Support, Containers, etc.).
  3. Ofrece borrar la .app + todos sus datos asociados.

Muy útil porque "arrastrar a la papelera" NO borra los datos en Library.
"""

import os
import plistlib
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

HOME = Path.home()

# Meses que consideramos "no usada hace mucho" y recomendamos desinstalar
UNUSED_THRESHOLD_DAYS = 180  # 6 meses

# Carpetas donde buscar datos relacionados a un bundle ID.
DATA_DIRS = [
    HOME / "Library" / "Application Support",
    HOME / "Library" / "Preferences",
    HOME / "Library" / "Caches",
    HOME / "Library" / "Containers",
    HOME / "Library" / "HTTPStorages",
    HOME / "Library" / "Saved Application State",
    HOME / "Library" / "WebKit",
    HOME / "Library" / "Cookies",
    HOME / "Library" / "LaunchAgents",
    HOME / "Library" / "Logs",
    HOME / "Library" / "Group Containers",
]

# Apps del sistema — no las mostramos porque no se pueden desinstalar.
SKIP_APP_PATHS = (
    "/System/",
    "/Applications/Utilities/",
)


def _read_bundle_id(app_path: Path) -> Optional[str]:
    plist = app_path / "Contents" / "Info.plist"
    if not plist.exists():
        return None
    try:
        with open(plist, "rb") as f:
            data = plistlib.load(f)
        val = data.get("CFBundleIdentifier")
        return val if isinstance(val, str) else None
    except Exception:
        return None


def _tree_size(path: Path) -> int:
    """Tamaño total de un archivo o carpeta."""
    import os
    if path.is_symlink():
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    try:
        for d, _, fs in os.walk(path, followlinks=False):
            for f in fs:
                try:
                    total += os.lstat(f"{d}/{f}").st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _get_last_used_date(app_path: Path) -> Optional[float]:
    """
    Devuelve el timestamp Unix del último uso de la app según Spotlight.
    Si no hay dato o falla, devuelve None.
    Usa `mdls -name kMDItemLastUsedDate`.
    """
    try:
        out = subprocess.run(
            ["mdls", "-raw", "-name", "kMDItemLastUsedDate", str(app_path)],
            capture_output=True, text=True, timeout=3,
        )
        raw = (out.stdout or "").strip()
        if not raw or raw == "(null)":
            return None
        # Formato típico: 2024-11-15 14:32:11 +0000
        dt = datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
        return dt.timestamp()
    except Exception:
        return None


def _months_ago(ts: Optional[float]) -> Optional[int]:
    if ts is None:
        return None
    days = (time.time() - ts) / 86400
    return int(days / 30)


def list_installed_apps() -> List[dict]:
    """
    Devuelve lista de apps instaladas.
    Dispatch: en Windows usa uninstaller_windows.py (registry).
    En macOS escanea /Applications.
    """
    import sys
    if sys.platform.startswith("win"):
        from uninstaller_windows import list_installed_apps as _win_list
        return _win_list()

    """
    Devuelve lista de apps instaladas por el usuario en /Applications.
    Cada app: {name, path, bundle_id, size, last_used, months_unused, recommend, reason}
    Ordenada: las "no usadas hace mucho" primero (recomendadas para desinstalar).
    """
    apps = []
    root = Path("/Applications")
    if not root.exists():
        return apps
    seen_bundle = set()
    for entry in root.rglob("*.app"):
        s = str(entry)
        if any(skip in s for skip in SKIP_APP_PATHS):
            continue
        parent_parts = entry.parent.parts
        if any(p.endswith(".app") for p in parent_parts):
            continue
        bundle_id = _read_bundle_id(entry)
        if not bundle_id or bundle_id in seen_bundle:
            continue
        seen_bundle.add(bundle_id)
        try:
            size = _tree_size(entry)
        except Exception:
            size = 0

        last_used = _get_last_used_date(entry)
        months = _months_ago(last_used)
        recommend = None
        reason = ""
        if last_used is None:
            reason = "Sin registro de uso reciente."
        elif months is not None and months >= (UNUSED_THRESHOLD_DAYS // 30):
            recommend = "uninstall"
            reason = f"No la abrís hace {months} meses. Considerá quitarla."

        apps.append({
            "name": entry.stem,
            "path": entry,
            "bundle_id": bundle_id,
            "size": size,
            "last_used": last_used,
            "months_unused": months,
            "recommend": recommend,
            "reason": reason,
        })

    # Ordenar: recomendadas primero (más viejas al tope), después alfabético
    def sort_key(a):
        if a["recommend"] == "uninstall":
            # dentro de "recomendar", ordenar por más meses sin uso primero
            return (0, -(a["months_unused"] or 0), a["name"].lower())
        return (1, a["name"].lower())

    apps.sort(key=sort_key)
    return apps


def find_related_paths(bundle_id: str, app_name: str) -> List[Path]:
    """
    Busca en ~/Library todos los archivos/carpetas que pertenecen a esta app,
    matcheando por bundle ID exacto o por prefijo (com.foo.bar.*).
    """
    bid_lower = bundle_id.lower()
    matches: List[Path] = []
    seen = set()
    for base in DATA_DIRS:
        if not base.exists():
            continue
        try:
            for entry in base.iterdir():
                name = entry.name
                # Quitar extensiones
                stem = name
                for ext in (".plist", ".savedState", ".binarycookies", ".sfl2", ".sfl3"):
                    if stem.endswith(ext):
                        stem = stem[: -len(ext)]
                        break
                stem_l = stem.lower()
                # Match exacto o subdominio del bundle ID
                if stem_l == bid_lower or stem_l.startswith(bid_lower + "."):
                    key = str(entry.resolve()) if entry.exists() else str(entry)
                    if key not in seen:
                        seen.add(key)
                        matches.append(entry)
        except OSError:
            continue
    return matches


def get_uninstall_targets(app: dict) -> dict:
    """
    Reúne .app + rutas relacionadas + tamaño total a liberar.
    """
    related = find_related_paths(app["bundle_id"], app["name"])
    all_paths = [app["path"]] + related
    total = app["size"] + sum(_tree_size(p) for p in related)
    return {
        "app": app,
        "app_path": app["path"],
        "related_paths": related,
        "all_paths": all_paths,
        "total_bytes": total,
    }


def is_app_running(app_name: str) -> bool:
    """Detecta si la .app está actualmente corriendo (compat)."""
    import sys
    if sys.platform.startswith("win"):
        from uninstaller_windows import is_app_running as _win
        return _win(app_name)
    return len(find_related_processes(app_name, "")) > 0


def find_related_processes(app_name: str, bundle_id: str) -> List[dict]:
    """Dispatch por plataforma."""
    import sys
    if sys.platform.startswith("win"):
        from uninstaller_windows import find_related_processes as _win
        return _win(app_name, bundle_id)
    return _find_related_processes_mac(app_name, bundle_id)


def _find_related_processes_mac(app_name: str, bundle_id: str) -> List[dict]:
    """
    Encuentra procesos relacionados con una app, incluyendo helpers en segundo plano.

    Estrategias combinadas (más recall que precisión):
      1. `pgrep -f "/AppName.app/"`      → procesos con el .app en su command line
      2. `pgrep -f "<bundle_id>"`         → helpers con el bundle ID (com.foo.helper, etc.)
      3. `pgrep -i "<AppShortName>"`      → matcheo por nombre corto (SafeCase i-insensitive)
      4. `lsof +D "/Applications/App.app"` → cualquier proceso con file handles abiertos ahí

    Filtra procesos del sistema y el mismo Python de CleanMyCompu.

    Devuelve: [{"pid": int, "name": str}, ...] deduplicado
    """
    procs: dict[int, str] = {}
    my_pid = os.getpid()

    patterns = [f"/{app_name}.app/"]
    if bundle_id:
        patterns.append(bundle_id)
        # También primer segmento tipo "com.easeus"
        vendor = ".".join(bundle_id.split(".")[:2])
        if vendor and vendor != bundle_id:
            patterns.append(vendor)
    # Nombre corto sin espacios (útil para helpers tipo "RecExpertsHelper")
    short = app_name.replace(" ", "")
    if len(short) >= 4:
        patterns.append(short)

    for pattern in patterns:
        try:
            out = subprocess.run(
                ["pgrep", "-f", pattern],
                capture_output=True, text=True, timeout=3,
            )
            for pid_str in out.stdout.strip().split("\n"):
                pid_str = pid_str.strip()
                if not pid_str:
                    continue
                try:
                    pid = int(pid_str)
                except ValueError:
                    continue
                if pid == my_pid or pid in procs:
                    continue
                # Traer el nombre del proceso
                name = _get_proc_name(pid)
                if not name or _is_system_process(name):
                    continue
                # Filtro sanity: el nombre o command debe contener algo relacionado
                # (evita falsos positivos de pgrep cuando el pattern es corto)
                if not _looks_related(name, app_name, bundle_id):
                    continue
                procs[pid] = name
        except Exception:
            continue

    return [{"pid": pid, "name": name} for pid, name in procs.items()]


def _get_proc_name(pid: int) -> Optional[str]:
    try:
        out = subprocess.run(
            ["ps", "-p", str(pid), "-o", "comm="],
            capture_output=True, text=True, timeout=2,
        )
        name = out.stdout.strip()
        # ps devuelve el path completo — tomamos el basename
        return name.split("/")[-1] if name else None
    except Exception:
        return None


_SYSTEM_PROC_PREFIXES = ("launchd", "kernel_task", "WindowServer", "loginwindow", "Finder")


def _is_system_process(name: str) -> bool:
    return any(name.startswith(p) for p in _SYSTEM_PROC_PREFIXES)


def _looks_related(proc_name: str, app_name: str, bundle_id: str) -> bool:
    n = proc_name.lower().replace(" ", "")
    a = app_name.lower().replace(" ", "")
    if a and a in n:
        return True
    if bundle_id:
        # Ej.: proceso "RecExperts", bundle "com.easeus.RecExperts" → suffix match
        last_seg = bundle_id.lower().split(".")[-1]
        if last_seg and last_seg in n:
            return True
    return False


_ADMIN_SAFE_ROOTS = (
    "/Applications/",
    "/Library/Application Support/",
    "/Library/LaunchAgents/",
    "/Library/LaunchDaemons/",
    "/Library/Preferences/",
    "/Library/PrivilegedHelperTools/",
    "/Library/Caches/",
    f"{HOME}/Library/",
)


def _is_admin_safe_path(p) -> bool:
    """
    Whitelisting: solo permitimos borrar con sudo cosas dentro de /Applications
    o /Library. Nunca en / o en carpetas del usuario tipo Documents.
    """
    try:
        s = str(Path(p).resolve()) if Path(p).exists() else str(p)
    except Exception:
        return False
    return any(s.startswith(root) for root in _ADMIN_SAFE_ROOTS)


def uninstall_with_admin(paths: list) -> dict:
    """
    Borra paths que requieren permisos de administrador (apps instaladas via
    .pkg tienen ownership de root).

    macOS muestra el diálogo NATIVO pidiendo la contraseña del usuario. Si
    el usuario cancela, retorna sin borrar nada.

    Solo permite paths dentro de /Applications o /Library por seguridad.

    Devuelve: {
        "success": bool,
        "freed": bytes efectivos liberados,
        "failed": paths que siguieron sin borrarse,
        "error": str ("cancelled" si el user rechazó la pass, "" si todo OK,
                       o el mensaje de error real),
    }
    """
    import json
    import shlex

    safe = [Path(p) for p in paths if _is_admin_safe_path(p)]
    unsafe = [Path(p) for p in paths if not _is_admin_safe_path(p)]

    if not safe:
        return {"success": False, "freed": 0, "failed": [Path(p) for p in paths],
                "error": "Ninguna de las rutas está en un directorio permitido."}

    # Tamaño antes del borrado
    freed_expected = sum(_tree_size(p) for p in safe if p.exists())

    # Construimos un for-loop que hace 3 cosas antes de intentar borrar:
    #   1. chflags -R noschg,nouchg  → quita flag de "system immutable"
    #      (algunos instaladores comerciales — EaseUS, Wondershare — lo ponen)
    #   2. xattr -rc                  → quita atributos extendidos (quarantine, etc.)
    #   3. mv a la Papelera (más limpio que rm)
    #   4. si mv falla → rm -rf directo
    # Además hacemos `set -e` OFF y ecoamos los errores por path para diagnóstico.
    quoted = " ".join(shlex.quote(str(p)) for p in safe)
    trash = shlex.quote(str(HOME / ".Trash"))
    sh_cmd = (
        f'TRASH={trash}; '
        f'for p in {quoted}; do '
        '  if [ ! -e "$p" ]; then echo "MISSING: $p" >&2; continue; fi; '
        '  chflags -R noschg,nouchg "$p" 2>/dev/null || true; '
        '  xattr -rc "$p" 2>/dev/null || true; '
        '  base=$(basename "$p"); '
        '  target="$TRASH/$base"; '
        # si ya hay algo con ese nombre en Trash, sufijo timestamp para no chocar
        '  if [ -e "$target" ]; then target="$target.$(date +%s)"; fi; '
        '  if ! mv -f "$p" "$target" 2>/dev/null; then '
        '    if ! rm -rf "$p" 2>/dev/null; then '
        '      echo "FAIL: $p" >&2; '
        '    fi; '
        '  fi; '
        'done'
    )
    apple_script = (
        f"do shell script {json.dumps(sh_cmd)} "
        f'with administrator privileges'
    )

    try:
        result = subprocess.run(
            ["osascript", "-e", apple_script],
            capture_output=True, text=True, timeout=180,
        )
    except Exception as e:
        return {"success": False, "freed": 0,
                "failed": [Path(p) for p in paths], "error": str(e)}

    err_text = (result.stderr or "").strip()

    if result.returncode != 0:
        # -128 = User canceled (o "User canceled")
        cancelled = (
            "-128" in err_text
            or "canceled" in err_text.lower()
            or "cancelled" in err_text.lower()
        )
        if cancelled:
            return {"success": False, "freed": 0,
                    "failed": [Path(p) for p in paths], "error": "cancelled"}
        # Cualquier otro error: seguimos para verificar qué quedó (parcial es posible)

    # Verificar qué quedó
    still = [p for p in safe if p.exists()]
    actual_freed = freed_expected - sum(_tree_size(p) for p in still)
    return {
        "success": len(still) == 0,
        "freed": max(0, actual_freed),
        "failed": still + unsafe,
        # Incluir stderr para diagnóstico si algo falló
        "error": err_text if still else "",
    }


def kill_processes(pids: List[int], force: bool = False,
                   wait_seconds: float = 0.8) -> List[int]:
    """Dispatch."""
    import sys
    if sys.platform.startswith("win"):
        from uninstaller_windows import kill_processes as _win
        return _win(pids, force, wait_seconds)
    return _kill_processes_mac(pids, force, wait_seconds)


def _kill_processes_mac(pids: List[int], force: bool = False,
                        wait_seconds: float = 0.8) -> List[int]:
    """
    Cierra una lista de procesos. Primero SIGTERM (limpio); si force=True,
    directamente SIGKILL.

    Devuelve la lista de PIDs que quedaron vivos después del intento.
    """
    import signal
    sig = signal.SIGKILL if force else signal.SIGTERM
    for pid in pids:
        try:
            os.kill(pid, sig)
        except (OSError, ProcessLookupError):
            pass  # ya estaba muerto, o sin permisos
    time.sleep(wait_seconds)
    still_alive = []
    for pid in pids:
        try:
            os.kill(pid, 0)  # 0 = solo chequear si sigue vivo
            still_alive.append(pid)
        except OSError:
            pass
    return still_alive


def _unload_launch_agent(plist_path: Path):
    """
    Desengancha un LaunchAgent de launchd antes de borrarlo.
    Sin esto, launchd sigue con el label registrado y algunos agents
    (updaters de Adobe/Google/Docker) relanzan la app al toque.
    """
    if plist_path.suffix != ".plist":
        return
    # El "label" suele ser el nombre del archivo sin .plist
    label = plist_path.stem
    uid = os.getuid()
    # bootout es el reemplazo moderno de "launchctl unload"
    for cmd in (
        ["launchctl", "bootout", f"gui/{uid}/{label}"],
        ["launchctl", "unload", "-w", str(plist_path)],  # fallback legacy
    ):
        try:
            subprocess.run(cmd, capture_output=True, timeout=5)
        except Exception:
            pass


def uninstall_app(target: dict,
                  on_progress: Optional[Callable[[str], None]] = None) -> dict:
    """Dispatch por plataforma."""
    import sys
    if sys.platform.startswith("win"):
        from uninstaller_windows import uninstall_app as _win
        return _win(target, on_progress)
    return _uninstall_app_mac(target, on_progress)


def _uninstall_app_mac(target: dict,
                       on_progress: Optional[Callable[[str], None]] = None) -> dict:
    """
    Desinstala una app y sus rastros.

    Estrategia por seguridad:
      - Para .plist de LaunchAgents: primero `launchctl bootout` (así launchd
        se olvida del label y no relanza el binario), después mover a Papelera.
      - Para todo lo demás: mover a Papelera con send2trash (reversible).
      - Al terminar, verificamos que cada path ya NO exista. Si sigue
        (permiso denegado, archivo bloqueado por proceso), lo devolvemos
        en failed_paths para que la UI se lo pueda decir al usuario.

    Devuelve: {"freed": bytes_liberados, "failed": [paths que no se pudieron borrar]}
    """
    from send2trash import send2trash

    freed = 0
    failed: List[Path] = []

    for raw in target["all_paths"]:
        p = Path(raw)
        if not p.exists():
            continue

        # 1) Desactivar LaunchAgent si aplica
        if p.suffix == ".plist" and "LaunchAgents" in str(p):
            _unload_launch_agent(p)

        # 2) Mover a Papelera
        try:
            size = _tree_size(p)
            send2trash(str(p))
            if on_progress:
                on_progress(f"→ Papelera: {p.name}")
        except Exception:
            failed.append(p)
            continue

        # 3) Verificar que realmente se fue
        if p.exists():
            failed.append(p)
        else:
            freed += size

    return {"freed": freed, "failed": failed}
