"""
Verificación de actualizaciones de CleanMyCompu.

Estrategia simple:
  - La app consulta una URL con un JSON manifest {"version", "url", "notes"}.
  - Si hay una versión mayor a __version__, notifica al usuario.
  - Click en la notif/indicator abre la URL en el navegador default.

Para publicar una nueva versión:
  1. Subí el .dmg a GitHub Releases (o donde sea).
  2. Actualizá latest.json en la URL de MANIFEST_URL con los datos de la release.
  3. Levantá __version__ acá y en el próximo build del .app.

Errores de red son silenciosos (nunca queremos molestar al usuario si su wifi
no funciona o si la URL cayó).
"""

import json
from urllib.request import Request, urlopen
from typing import Optional


__version__ = "1.4.0"

# URL con el JSON de la última versión.
# Formato esperado del JSON:
#   {"version": "1.2.0",
#    "url": "https://github.com/USER/CleanMyCompu/releases/download/v1.2.0/CleanMyCompu.dmg",
#    "notes": "- Agregado X\n- Fixed Y"}
#
# Cuando publiques la primera release en GitHub, cambiá esta URL por la real.
# Mientras tanto, la URL abajo va a 404 silencioso — la app no molesta.
MANIFEST_URL = (
    "https://raw.githubusercontent.com/mogwai-arg/CleanMyCompu/main/latest.json"
)


def check_for_update() -> Optional[dict]:
    """
    Consulta el manifest. Devuelve:
      - dict {"version", "url", "notes", "current"} si hay update disponible
      - None si no hay update, o si la consulta falló (silencioso)
    """
    try:
        req = Request(MANIFEST_URL,
                      headers={"User-Agent": f"CleanMyCompu/{__version__}"})
        with urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None

    if not isinstance(data, dict):
        return None
    newer = data.get("version")
    if not newer or not _is_newer(str(newer), __version__):
        return None
    return {
        "version": str(newer),
        "url": str(data.get("url") or ""),
        "notes": str(data.get("notes") or ""),
        "current": __version__,
    }


def _is_newer(new: str, current: str) -> bool:
    """Comparación semver simple (major.minor.patch)."""
    def parts(v: str):
        return tuple(int(x) for x in v.split(".") if x.isdigit())
    try:
        return parts(new) > parts(current)
    except Exception:
        return False


def open_download_page(url: str):
    """Abre la URL en el navegador default del sistema."""
    if not url:
        return
    import webbrowser
    try:
        webbrowser.open(url)
    except Exception:
        pass
