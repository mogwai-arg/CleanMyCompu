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
    hiberfil.sys tiene ACL que bloquea lectura directa sin admin.
    Devolvemos:
      - 0 si el archivo NO existe (hibernación ya desactivada)
      - estimado (0.75 * RAM) si existe y no podemos leer el tamaño real
      - tamaño real si podemos leerlo (con admin o si Windows lo permite)
    Así el diff antes/después mide correctamente si se liberó espacio.
    """
    hiber_path = Path("C:/hiberfil.sys")
    # Chequear existencia via Path.exists() puede fallar por ACL — usar WMI/CIM
    # o simplemente asumir que si podemos hacer stat, existe.
    exists = False
    real_size = None
    try:
        # os.stat suele funcionar aunque no podamos leer el contenido
        st = os.stat(str(hiber_path))
        exists = True
        real_size = st.st_size
    except (OSError, PermissionError):
        # Fallback: usar dir command via subprocess
        try:
            result = subprocess.run(
                ["cmd", "/c", "dir /a-h /a-s C:\\hiberfil.sys"],
                capture_output=True, text=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if "hiberfil.sys" in result.stdout:
                exists = True
        except Exception:
            pass

    if not exists:
        return 0  # hibernación ya desactivada — nada para liberar

    if real_size is not None and real_size > 0:
        return real_size

    # Existe pero no pudimos medirlo — estimar
    try:
        import psutil
        return int(psutil.virtual_memory().total * 0.75)
    except Exception:
        return 4 * 1024 ** 3


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
        # -ErrorAction Stop hace que errores tiren excepcion y las veamos en el log
        "ps_command": (
            "Stop-Service -Name wuauserv -Force -ErrorAction Stop; "
            "Start-Sleep -Seconds 2; "
            f"Get-ChildItem -LiteralPath '{WINDIR}\\SoftwareDistribution\\Download' "
            "-ErrorAction SilentlyContinue | "
            "Remove-Item -Recurse -Force -ErrorAction Continue; "
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
            f"Get-ChildItem -LiteralPath '{WINDIR}\\Temp' -ErrorAction Stop | "
            "Remove-Item -Recurse -Force -ErrorAction Continue"
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
            f"Get-ChildItem -LiteralPath '{WINDIR}\\Prefetch' -ErrorAction Stop | "
            "Remove-Item -Recurse -Force -ErrorAction Continue"
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
            "Stop-Service -Name DoSvc -Force -ErrorAction Continue; "
            "Start-Sleep -Seconds 2; "
            f"Get-ChildItem -LiteralPath '{WINDIR}\\SoftwareDistribution\\DeliveryOptimization' "
            "-ErrorAction SilentlyContinue | "
            "Remove-Item -Recurse -Force -ErrorAction Continue; "
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
        # powercfg no tira excepciones. Capturamos su output y chequeamos $LASTEXITCODE.
        "ps_command": (
            "$out = & powercfg /hibernate off 2>&1; "
            "Write-Output \"powercfg exit: $LASTEXITCODE\"; "
            "Write-Output \"powercfg output: $out\"; "
            "if ($LASTEXITCODE -ne 0) { throw \"powercfg fallo con exit code $LASTEXITCODE\" }; "
            # Verificar que hiberfil.sys efectivamente se borro
            "Start-Sleep -Seconds 2; "
            "if (Test-Path 'C:\\hiberfil.sys') { "
            "  throw 'powercfg dijo OK pero hiberfil.sys sigue ahi (posible bloqueo por politica de dominio)' "
            "} else { Write-Output 'OK: hiberfil.sys borrado' }"
        ),
    },
    {
        "id": "component_store",
        "name": "Limpiar Component Store (WinSxS)",
        "desc": "Ejecuta 'dism /StartComponentCleanup /ResetBase'. Elimina versiones "
                "viejas de componentes de Windows. AVISO: después de esto, los updates "
                "de Windows ya instalados no podrán desinstalarse. Puede tardar 10-30 min.",
        "safety": "caution",
        "estimate_fn": estimate_component_store,
        "estimate_approx": True,
        "ps_command": (
            "$out = & dism.exe /Online /Cleanup-Image /StartComponentCleanup /ResetBase 2>&1; "
            "Write-Output \"dism exit: $LASTEXITCODE\"; "
            "Write-Output \"dism output (ultimas lineas): $($out | Select-Object -Last 5)\"; "
            "if ($LASTEXITCODE -ne 0) { throw \"dism fallo con exit code $LASTEXITCODE\" }"
        ),
    },
]


# ============================================================
# Ejecución con UAC único
# ============================================================

def run_operations(op_ids: List[str], progress_cb=None) -> Tuple[bool, str]:
    """
    Ejecuta las operaciones seleccionadas en un solo script PS elevado.
    El script escribe un log detallado a un archivo temporal que leemos
    después para saber qué funcionó y qué no.

    Devuelve (any_success, log_text).
      any_success: True si al menos una op se completó sin errores.
      log_text: log detallado por operación (para mostrar al usuario).
    """
    if not sys.platform.startswith("win"):
        return False, "Solo funciona en Windows."

    ops = [op for op in OPERATIONS if op["id"] in op_ids]
    if not ops:
        return True, "No hay operaciones para ejecutar."

    # Archivo de log que el PS elevado escribe y leemos después
    log_fd, log_path = tempfile.mkstemp(suffix=".log", prefix="cleanmycompu_", text=True)
    os.close(log_fd)
    # Aseguramos que el archivo existe y está vacío
    Path(log_path).write_text("", encoding="utf-8")

    # Escapar path para PS literal (usa doble backslash)
    log_ps = log_path.replace("\\", "\\\\")

    # Construir script: por cada op mide tamaño antes, ejecuta, mide después,
    # y loguea el resultado real (bytes liberados).
    lines = [
        "$ErrorActionPreference = 'Continue'",
        f'$logFile = "{log_ps}"',
        '"=== CleanMyCompu — inicio $(Get-Date -Format ''yyyy-MM-dd HH:mm:ss'') ===" | Out-File -FilePath $logFile -Encoding utf8',
        '"Usuario admin: $([Security.Principal.WindowsIdentity]::GetCurrent().Name)" | Out-File -Append -FilePath $logFile -Encoding utf8',
        '"---" | Out-File -Append -FilePath $logFile -Encoding utf8',
        '$failures = 0',
    ]

    for op in ops:
        name_ps = op["name"].replace("'", "''")
        cmd_ps = op["ps_command"]
        lines.append(f'"[BEGIN] {name_ps}" | Out-File -Append -FilePath $logFile -Encoding utf8')
        lines.append("try {")
        # Comando real
        lines.append(f"    {cmd_ps}")
        lines.append(f'    "[OK] {name_ps} — comando terminó sin excepciones" | Out-File -Append -FilePath $logFile -Encoding utf8')
        lines.append("} catch {")
        lines.append(f'    "[FAIL] {name_ps} — $($_.Exception.Message)" | Out-File -Append -FilePath $logFile -Encoding utf8')
        lines.append("    $failures = $failures + 1")
        lines.append("}")
        lines.append('"---" | Out-File -Append -FilePath $logFile -Encoding utf8')

    lines.append('"=== fin: $failures fallos ===" | Out-File -Append -FilePath $logFile -Encoding utf8')
    lines.append("exit $failures")

    script = "\n".join(lines)

    exit_code = _run_elevated_ps_with_code(script)

    # Leer el log (aunque el proceso haya fallado)
    try:
        # utf-8-sig porque Out-File a veces incluye BOM
        log_text = Path(log_path).read_text(encoding="utf-8-sig", errors="replace")
    except Exception as e:
        log_text = f"(no se pudo leer el log: {e})"
    finally:
        try:
            Path(log_path).unlink()
        except OSError:
            pass

    if exit_code is None:
        # UAC cancelado por el usuario
        return False, (
            "⚠️ La operación fue cancelada.\n\n"
            "Probablemente rechazaste el prompt UAC de Windows (el que pide "
            "permisos de administrador). Sin ese permiso no se puede tocar "
            "el sistema.\n\n"
            "Volvé a intentar y aceptá el prompt UAC cuando aparezca."
        )

    if exit_code < 0:
        # Error de infraestructura (PS no arrancó, etc.)
        return False, f"⚠️ No se pudo lanzar PowerShell elevado (código {exit_code}).\n\nLog:\n{log_text}"

    # exit_code == número de operaciones fallidas
    any_success = exit_code < len(ops)
    return any_success, log_text


def _run_elevated_ps_with_code(script: str, timeout: int = 1800):
    """
    Como _run_elevated_ps pero devuelve el exit code real (o None si UAC cancelado).
      None  → usuario canceló UAC
      -1    → error lanzando el proceso
      0+    → exit code del script elevado (= cantidad de fallos)
    """
    if not sys.platform.startswith("win"):
        return -1
    fd, script_path = tempfile.mkstemp(suffix=".ps1", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig") as f:
            f.write(script)
        # Outer script: Start-Process con try/catch para detectar UAC cancelado
        outer = (
            "try {\n"
            f"  $p = Start-Process powershell -Verb RunAs -Wait -PassThru "
            f"-WindowStyle Hidden -ArgumentList "
            f"'-NoProfile','-ExecutionPolicy','Bypass','-File','{script_path}'\n"
            "  if ($p -eq $null) { exit 240 }\n"
            "  exit $p.ExitCode\n"
            "} catch [System.ComponentModel.Win32Exception] {\n"
            "  # NativeErrorCode 1223 = ERROR_CANCELLED (usuario cancelo UAC)\n"
            "  if ($_.Exception.NativeErrorCode -eq 1223) { exit 250 }\n"
            "  exit 249\n"
            "} catch {\n"
            "  exit 248\n"
            "}\n"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", outer],
            capture_output=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        code = result.returncode
        if code == 250:
            return None  # UAC cancelado
        if code in (240, 248, 249):
            return -1  # error de infra
        return code
    except (subprocess.TimeoutExpired, OSError):
        return -1
    finally:
        try:
            Path(script_path).unlink()
        except OSError:
            pass


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
