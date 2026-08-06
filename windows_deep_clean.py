"""
Limpieza avanzada de Windows: operaciones que necesitan permisos de administrador
y liberan típicamente 10-30 GB combinadas.

Todas usan comandos oficiales/documentados por Microsoft y son SEGURAS:
  - Caché de Windows Update (SoftwareDistribution\\Download)
  - Archivos temporales del sistema (%WINDIR%\\Temp)
  - Prefetch (regenerable)
  - Delivery Optimization files
  - Component Store (dism /StartComponentCleanup /ResetBase)
  - hiberfil.sys (powercfg /hibernate off)

Ejecutamos TODAS las seleccionadas en un solo script PowerShell con UAC único.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

WINDIR = os.environ.get("WINDIR", r"C:\Windows")


def _dir_size(path: Path) -> int:
    """Suma bytes recursivamente. Tolera PermissionError."""
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
# Estimaciones de tamaño (sin admin — pueden subestimar)
# ============================================================

def estimate_wu_cache() -> int:
    return _dir_size(Path(WINDIR) / "SoftwareDistribution" / "Download")


def estimate_temp() -> int:
    return _dir_size(Path(WINDIR) / "Temp")


def estimate_prefetch() -> int:
    return _dir_size(Path(WINDIR) / "Prefetch")


def estimate_delivery_opt() -> int:
    return _dir_size(Path(WINDIR) / "SoftwareDistribution" / "DeliveryOptimization")


def estimate_hiberfil() -> int:
    """
    hiberfil.sys tiene ACL que bloquea lectura sin admin. Estimamos
    según convención de Microsoft: 0.75 * RAM total.
    """
    try:
        import psutil
        return int(psutil.virtual_memory().total * 0.75)
    except Exception:
        return 4 * 1024 ** 3  # fallback 4 GB


def estimate_component_store() -> int:
    """
    No podemos correr 'dism /AnalyzeComponentStore' sin admin. Estimamos
    tamaño total de WinSxS (sobreestima, porque WinSxS usa hard-links).
    Devolvemos ese valor pero con flag "aprox".
    """
    return _dir_size(Path(WINDIR) / "WinSxS")


# ============================================================
# Definición de operaciones
# ============================================================
# Cada op:
#   id: identificador
#   name: título humano
#   desc: qué hace en lenguaje simple
#   safety: 'safe' (100% recomendado) | 'caution' (irreversible / requiere pensarlo)
#   estimate_fn: función que devuelve bytes
#   estimate_approx: si True, el número mostrado es aproximado
#   ps_command: comando PowerShell que ejecuta la op (se corre elevado)

OPERATIONS = [
    {
        "id": "wu_cache",
        "name": "Caché de Windows Update",
        "desc": "Borra descargas de updates de Windows que ya se instalaron. "
                "Windows los volverá a bajar solo si los necesita.",
        "safety": "safe",
        "estimate_fn": estimate_wu_cache,
        "estimate_approx": False,
        "ps_command": (
            "Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue; "
            f"Remove-Item -LiteralPath '{WINDIR}\\SoftwareDistribution\\Download\\*' "
            "-Recurse -Force -ErrorAction SilentlyContinue; "
            "Start-Service -Name wuauserv -ErrorAction SilentlyContinue"
        ),
    },
    {
        "id": "temp",
        "name": "Archivos temporales del sistema",
        "desc": "Borra %WINDIR%\\Temp. Los archivos que estén en uso quedan intactos.",
        "safety": "safe",
        "estimate_fn": estimate_temp,
        "estimate_approx": False,
        "ps_command": (
            f"Remove-Item -LiteralPath '{WINDIR}\\Temp\\*' "
            "-Recurse -Force -ErrorAction SilentlyContinue"
        ),
    },
    {
        "id": "prefetch",
        "name": "Caché Prefetch",
        "desc": "Datos que Windows usa para acelerar el arranque de programas. "
                "Se regeneran automáticamente en los próximos días.",
        "safety": "safe",
        "estimate_fn": estimate_prefetch,
        "estimate_approx": False,
        "ps_command": (
            f"Remove-Item -LiteralPath '{WINDIR}\\Prefetch\\*' "
            "-Recurse -Force -ErrorAction SilentlyContinue"
        ),
    },
    {
        "id": "delivery_opt",
        "name": "Delivery Optimization",
        "desc": "Archivos que Windows comparte con otras PCs en tu red para acelerar "
                "descargas de updates. Se regeneran solos.",
        "safety": "safe",
        "estimate_fn": estimate_delivery_opt,
        "estimate_approx": False,
        "ps_command": (
            "Stop-Service -Name DoSvc -Force -ErrorAction SilentlyContinue; "
            f"Remove-Item -LiteralPath '{WINDIR}\\SoftwareDistribution\\DeliveryOptimization\\*' "
            "-Recurse -Force -ErrorAction SilentlyContinue; "
            "Start-Service -Name DoSvc -ErrorAction SilentlyContinue"
        ),
    },
    {
        "id": "hibernate",
        "name": "Desactivar hibernación (borra hiberfil.sys)",
        "desc": "Si nunca usás la opción 'Hibernar' (distinta de 'Suspender'), este "
                "archivo del tamaño de tu RAM está ocupando espacio sin motivo. "
                "Podés reactivar hibernación en cualquier momento con "
                "'powercfg /hibernate on'.",
        "safety": "caution",
        "estimate_fn": estimate_hiberfil,
        "estimate_approx": True,
        "ps_command": "powercfg /hibernate off",
    },
    {
        "id": "component_store",
        "name": "Limpiar Component Store (WinSxS)",
        "desc": "Ejecuta 'dism /StartComponentCleanup /ResetBase'. Elimina versiones "
                "viejas de componentes de Windows. AVISO: después de esto, los updates "
                "de Windows ya instalados no podrán desinstalarse. Puede tardar 10-30 min.",
        "safety": "caution",
        "estimate_fn": estimate_component_store,
        "estimate_approx": True,  # el tamaño real recuperable es menor por hard-links
        "ps_command": "dism.exe /Online /Cleanup-Image /StartComponentCleanup /ResetBase",
    },
]


# ============================================================
# Ejecución con UAC único
# ============================================================

def run_operations(op_ids: List[str], progress_cb=None) -> Tuple[bool, str]:
    """
    Ejecuta las operaciones seleccionadas en un solo script PS elevado.
    Devuelve (success, message).
    """
    if not sys.platform.startswith("win"):
        return False, "Solo funciona en Windows."

    ops = [op for op in OPERATIONS if op["id"] in op_ids]
    if not ops:
        return True, "No hay operaciones para ejecutar."

    # Construir script con manejo de errores individual + logging
    lines = ["$ErrorActionPreference = 'Continue'", "$log = @()"]
    for op in ops:
        name = op["name"].replace("'", "''")
        cmd = op["ps_command"]
        lines.append("Write-Host '=== " + name + " ==='")
        lines.append("try {")
        lines.append("    " + cmd)
        lines.append("    $log += '[OK] " + name + "'")
        lines.append("} catch {")
        lines.append("    $log += '[FAIL] " + name + ": ' + $_.Exception.Message")
        lines.append("}")
    lines.append("$log | Out-String | Write-Host")
    lines.append("exit 0")
    script = "\n".join(lines)

    success = _run_elevated_ps(script)
    if success:
        return True, "Limpieza completada."
    return False, "La operación fue cancelada o falló (¿rechazaste el prompt UAC?)."


def _run_elevated_ps(script: str, timeout: int = 1800) -> bool:
    """
    Escribe el script a un .ps1 temporal y lo lanza con Start-Process -Verb RunAs.
    Timeout largo (30 min) porque dism puede tardar bastante.
    """
    if not sys.platform.startswith("win"):
        return False
    fd, script_path = tempfile.mkstemp(suffix=".ps1", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig") as f:
            f.write(script)
        outer = (
            f"$p = Start-Process powershell -Verb RunAs -Wait -PassThru "
            f"-WindowStyle Hidden -ArgumentList "
            f"'-NoProfile','-ExecutionPolicy','Bypass','-File','{script_path}'; "
            f"exit $p.ExitCode"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", outer],
            capture_output=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False
    finally:
        try:
            Path(script_path).unlink()
        except OSError:
            pass


def estimate_all() -> List[dict]:
    """
    Devuelve lista de dicts listos para la UI:
      { id, name, desc, safety, size, size_approx, ps_command }
    """
    out = []
    for op in OPERATIONS:
        try:
            size = op["estimate_fn"]()
        except Exception:
            size = 0
        out.append({
            "id": op["id"],
            "name": op["name"],
            "desc": op["desc"],
            "safety": op["safety"],
            "size": size,
            "size_approx": op["estimate_approx"],
        })
    return out
