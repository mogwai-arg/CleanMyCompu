"""
Actualizador de apps y paquetes en macOS.

MVP: solo Homebrew (formulae + casks). Es la fuente más común de apps y
CLI tools instaladas por usuarios técnicos. Extensible en el futuro a:
  - Mac App Store: via `mas` (necesita `brew install mas`)
  - App Store apps directas: via `softwareupdate --list --all`
"""

import json
import shutil
import subprocess
from typing import Callable, List, Optional


def is_brew_installed() -> bool:
    return shutil.which("brew") is not None


def brew_path() -> Optional[str]:
    return shutil.which("brew")


def list_outdated() -> List[dict]:
    """
    Lista paquetes de Homebrew con updates disponibles.
    Devuelve list de: {name, kind: 'formula'|'cask', current, latest}
    Ordenada alfabéticamente. Silencia errores.
    """
    if not is_brew_installed():
        return []
    try:
        result = subprocess.run(
            [brew_path(), "outdated", "--json=v2"],
            capture_output=True, text=True, timeout=60,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout or "{}")
    except Exception:
        return []

    results = []
    for pkg in data.get("formulae", []):
        versions = pkg.get("installed_versions", [])
        results.append({
            "name": pkg.get("name", "?"),
            "kind": "formula",
            "current": versions[0] if versions else "?",
            "latest": pkg.get("current_version", "?"),
        })
    for pkg in data.get("casks", []):
        name = pkg.get("name") or pkg.get("token") or "?"
        if isinstance(name, list):
            name = name[0] if name else "?"
        current = pkg.get("installed_versions")
        if isinstance(current, list):
            current = current[0] if current else "?"
        results.append({
            "name": name,
            "kind": "cask",
            "current": current or "?",
            "latest": pkg.get("current_version", "?"),
        })
    results.sort(key=lambda x: x["name"].lower())
    return results


def upgrade_all(on_progress: Optional[Callable[[str], None]] = None) -> dict:
    """
    Corre `brew upgrade` streaming las líneas de output al callback.
    Devuelve {"success": bool, "output": str}
    """
    if not is_brew_installed():
        return {"success": False,
                "output": "Homebrew no está instalado. Instalalo desde brew.sh"}
    try:
        proc = subprocess.Popen(
            [brew_path(), "upgrade"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        lines = []
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.strip()
            if line:
                lines.append(line)
                if on_progress:
                    on_progress(line)
        proc.wait(timeout=1800)  # 30 min máximo
        return {"success": proc.returncode == 0, "output": "\n".join(lines)}
    except Exception as e:
        return {"success": False, "output": str(e)}


def upgrade_specific(names: List[str],
                     on_progress: Optional[Callable[[str], None]] = None) -> dict:
    """
    Corre `brew upgrade <nombres>` para actualizar solo los seleccionados.
    """
    if not is_brew_installed():
        return {"success": False, "output": "Homebrew no está instalado."}
    if not names:
        return {"success": True, "output": ""}
    try:
        proc = subprocess.Popen(
            [brew_path(), "upgrade", *names],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        lines = []
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.strip()
            if line:
                lines.append(line)
                if on_progress:
                    on_progress(line)
        proc.wait(timeout=1800)
        return {"success": proc.returncode == 0, "output": "\n".join(lines)}
    except Exception as e:
        return {"success": False, "output": str(e)}
