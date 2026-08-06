"""
Categorías de limpieza por sistema operativo.

Cada categoría tiene:
  - id: identificador único
  - group: agrupador para la UI (ej. "Sistema", "Navegadores", "Restos de programas")
  - name: nombre visible en la interfaz
  - icon: emoji simple para mostrar
  - description: qué es y por qué es seguro borrarlo
  - path_patterns: lista de rutas o patrones glob a escanear/limpiar
                   (soporta ~ para el home y * / ? / [] para comodines)
  - safety: "safe" (recomendado por defecto) o "caution" (requiere revisión)
"""

import sys


def is_mac() -> bool:
    return sys.platform == "darwin"


def is_windows() -> bool:
    return sys.platform.startswith("win")


CATEGORIES_MAC = [
    # ---------------- SISTEMA ----------------
    {
        "id": "system_cache",
        "group": "Sistema",
        "name": "Cachés del sistema",
        "icon": "sparkles",
        "description": (
            "Archivos temporales que las apps generan para funcionar más rápido. "
            "Es seguro borrarlos: las apps los recrean cuando los necesitan."
        ),
        "path_patterns": ["~/Library/Caches"],
        "safety": "safe",
    },
    {
        "id": "system_logs",
        "group": "Sistema",
        "name": "Logs del sistema",
        "icon": "file-text",
        "description": (
            "Registros de actividad de tus apps. Ocupan espacio y raramente "
            "los necesitás salvo que estés diagnosticando un problema."
        ),
        "path_patterns": ["~/Library/Logs"],
        "safety": "safe",
    },
    {
        "id": "trash",
        "group": "Sistema",
        "name": "Papelera",
        "icon": "trash",
        "description": "Vacía tu papelera permanentemente para recuperar el espacio.",
        "path_patterns": ["~/.Trash"],
        "safety": "safe",
    },
    {
        "id": "quicklook_thumbs",
        "group": "Sistema",
        "name": "Miniaturas de QuickLook",
        "icon": "image",
        "description": (
            "Miniaturas que macOS genera al previsualizar archivos. Se regeneran solas."
        ),
        "path_patterns": ["~/Library/Caches/com.apple.QuickLook.thumbnailcache"],
        "safety": "safe",
    },
    {
        "id": "crash_reports",
        "group": "Sistema",
        "name": "Informes de fallos",
        "icon": "alert-triangle",
        "description": (
            "Reportes que macOS guarda cuando una app se cierra inesperadamente. "
            "Solo útiles para diagnóstico."
        ),
        "path_patterns": [
            "~/Library/Logs/DiagnosticReports",
            "~/Library/Application Support/CrashReporter",
        ],
        "safety": "safe",
    },

    # ---------------- NAVEGADORES ----------------
    {
        "id": "browser_chrome",
        "group": "Navegadores",
        "name": "Caché de Google Chrome",
        "icon": "globe",
        "description": (
            "Datos temporales de páginas visitadas en Chrome (todos los perfiles). "
            "Cerrá el navegador antes de limpiar."
        ),
        "path_patterns": [
            # Perfil Default + Profile 1, 2, etc. (usuarios con múltiples cuentas)
            "~/Library/Application Support/Google/Chrome/*/Cache",
            "~/Library/Application Support/Google/Chrome/*/Code Cache",
            "~/Library/Application Support/Google/Chrome/*/GPUCache",
            "~/Library/Application Support/Google/Chrome/*/Service Worker/CacheStorage",
            "~/Library/Application Support/Google/Chrome/*/Service Worker/ScriptCache",
            "~/Library/Application Support/Google/Chrome/*/Application Cache",
            "~/Library/Application Support/Google/Chrome/*/File System",
            "~/Library/Application Support/Google/Chrome/*/blob_storage",
            "~/Library/Application Support/Google/Chrome/ShaderCache",
            "~/Library/Application Support/Google/Chrome/GrShaderCache",
            "~/Library/Caches/Google/Chrome",
        ],
        "safety": "safe",
    },
    {
        "id": "browser_safari",
        "group": "Navegadores",
        "name": "Caché de Safari",
        "icon": "globe",
        "description": (
            "Datos temporales, storage y web data de Safari. Cerrá el navegador antes de limpiar."
        ),
        "path_patterns": [
            "~/Library/Caches/com.apple.Safari",
            "~/Library/Caches/com.apple.Safari.SafeBrowsing",
            "~/Library/Caches/com.apple.WebKit.PluginProcess",
            "~/Library/Safari/LocalStorage",
            "~/Library/Safari/Databases",
            "~/Library/WebKit/com.apple.Safari",
            "~/Library/Containers/com.apple.Safari/Data/Library/Caches",
        ],
        "safety": "safe",
    },
    {
        "id": "browser_firefox",
        "group": "Navegadores",
        "name": "Caché de Firefox",
        "icon": "globe",
        "description": (
            "Datos temporales de páginas visitadas en Firefox. Cerrá el navegador antes de limpiar."
        ),
        "path_patterns": [
            "~/Library/Caches/Firefox",
            "~/Library/Application Support/Firefox/Profiles/*/cache2",
            "~/Library/Application Support/Firefox/Profiles/*/startupCache",
        ],
        "safety": "safe",
    },
    {
        "id": "browser_edge",
        "group": "Navegadores",
        "name": "Caché de Microsoft Edge",
        "icon": "globe",
        "description": (
            "Datos temporales de páginas visitadas en Edge (todos los perfiles). "
            "Cerrá el navegador antes de limpiar."
        ),
        "path_patterns": [
            "~/Library/Application Support/Microsoft Edge/*/Cache",
            "~/Library/Application Support/Microsoft Edge/*/Code Cache",
            "~/Library/Application Support/Microsoft Edge/*/GPUCache",
            "~/Library/Application Support/Microsoft Edge/*/Service Worker/CacheStorage",
            "~/Library/Application Support/Microsoft Edge/ShaderCache",
        ],
        "safety": "safe",
    },
    {
        "id": "browser_brave",
        "group": "Navegadores",
        "name": "Caché de Brave",
        "icon": "globe",
        "description": (
            "Datos temporales de páginas visitadas en Brave (todos los perfiles). "
            "Cerrá el navegador antes de limpiar."
        ),
        "path_patterns": [
            "~/Library/Application Support/BraveSoftware/Brave-Browser/*/Cache",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/*/Code Cache",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/*/GPUCache",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/*/Service Worker/CacheStorage",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/ShaderCache",
        ],
        "safety": "safe",
    },
    {
        "id": "browser_cookies",
        "group": "Navegadores",
        "name": "Cookies de navegadores",
        "icon": "globe",
        "description": (
            "Cookies de Chrome, Edge, Brave y Firefox. Borrar cookies te desloguea "
            "de sitios web que tenías sesión iniciada — usalo si estás priorizando "
            "privacidad. Cerrá los navegadores primero."
        ),
        "path_patterns": [
            "~/Library/Application Support/Google/Chrome/*/Cookies",
            "~/Library/Application Support/Google/Chrome/*/Cookies-journal",
            "~/Library/Application Support/Microsoft Edge/*/Cookies",
            "~/Library/Application Support/Microsoft Edge/*/Cookies-journal",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/*/Cookies",
            "~/Library/Application Support/Firefox/Profiles/*/cookies.sqlite",
            "~/Library/Application Support/Firefox/Profiles/*/cookies.sqlite-wal",
            "~/Library/Cookies/Cookies.binarycookies",
        ],
        "safety": "caution",
    },

    # ---------------- RESTOS DE PROGRAMAS ----------------
    {
        "id": "adobe_leftovers",
        "group": "Restos de programas",
        "name": "Restos de Adobe",
        "icon": "palette",
        "description": (
            "Cachés, logs y preferencias que Adobe deja incluso después de actualizar "
            "o desinstalar sus programas (Photoshop, Acrobat, Creative Cloud, etc.). "
            "Suelen ocupar varios GB. Cerrá cualquier app de Adobe antes de limpiar."
        ),
        "path_patterns": [
            "~/Library/Application Support/Adobe",
            "~/Library/Application Support/CrashReporter/Adobe*",
            "~/Library/Preferences/com.adobe.*",
            "~/Library/Preferences/Adobe",
            "~/Library/Caches/com.adobe.*",
            "~/Library/Caches/Adobe",
            "~/Library/Logs/Adobe",
            "~/Library/Logs/CrashReporter/Adobe*",
            "~/Library/HTTPStorages/com.adobe.*",
            "~/Library/Cookies/com.adobe.*",
            "~/Library/Saved Application State/com.adobe.*",
            "~/Documents/Adobe/Common/Media Cache Files",
            "~/Documents/Adobe/Common/Media Cache",
            "~/Documents/Adobe/Premiere Pro/*/Adobe Premiere Pro Auto-Save",
            "~/Documents/Adobe/Premiere Pro/*/Adobe Premiere Pro Preview Files",
        ],
        "safety": "safe",
    },
    {
        "id": "ms_office_leftovers",
        "group": "Restos de programas",
        "name": "Restos de Microsoft Office",
        "icon": "file-text",
        "description": (
            "Cachés y datos temporales de Word, Excel, PowerPoint, Outlook y Teams. "
            "Cerrá estas apps antes de limpiar."
        ),
        "path_patterns": [
            "~/Library/Caches/com.microsoft.*",
            "~/Library/Application Support/Microsoft/Office/16.0/OfficeFileCache",
            "~/Library/Group Containers/UBF8T346G9.Office/Outlook/Outlook 15 Profiles/Main Profile/Data/Caches",
        ],
        "safety": "safe",
    },
    {
        "id": "app_updates",
        "group": "Restos de programas",
        "name": "Instaladores y actualizadores viejos",
        "icon": "box",
        "description": (
            "Archivos que quedan tras actualizar apps (Zoom, Chrome, Slack, Spotify, etc.). "
            "Ocupan espacio innecesario."
        ),
        "path_patterns": [
            "~/Library/Application Support/Zoom/Updates",
            "~/Library/Application Support/Google/GoogleUpdater",
            "~/Library/Application Support/Slack/Cache",
            "~/Library/Application Support/Slack/Service Worker/CacheStorage",
            "~/Library/Application Support/Spotify/PersistentCache",
            "~/Library/Caches/com.spotify.client",
            "~/Library/Application Support/discord/Cache",
            "~/Library/Application Support/discord/Code Cache",
        ],
        "safety": "safe",
    },
    {
        "id": "orphaned_apps",
        "group": "Restos de programas",
        "name": "Restos de apps desinstaladas",
        "icon": "ghost",
        "description": (
            "Datos en ~/Library que quedaron de apps que ya no están instaladas "
            "(detectado comparando con lo que hay en /Applications). "
            "Es una heurística: revisá antes de borrar."
        ),
        "path_provider": "orphaned_app_data",
        "safety": "caution",
    },
    {
        "id": "old_downloads",
        "group": "Restos de programas",
        "name": "Instaladores .dmg y .pkg viejos en Descargas",
        "icon": "hard-drive",
        "description": (
            "Archivos .dmg, .pkg y .zip en tu carpeta de Descargas de más de 30 días. "
            "Revisá antes de borrar por si hay algo importante."
        ),
        "path_patterns": [
            # este category usa scanning especial en scanner.py — path_patterns queda como referencia
            "~/Downloads/*.dmg",
            "~/Downloads/*.pkg",
        ],
        "safety": "caution",
        "min_age_days": 30,  # solo archivos más viejos que esto
    },

    # ---------------- DESARROLLO ----------------
    {
        "id": "xcode_derived",
        "group": "Desarrollo",
        "name": "Xcode: Datos derivados",
        "icon": "hammer",
        "description": (
            "Archivos que Xcode genera al compilar proyectos. Suelen ocupar muchos GB "
            "y se regeneran cuando volvés a compilar."
        ),
        "path_patterns": [
            "~/Library/Developer/Xcode/DerivedData",
            "~/Library/Developer/Xcode/Archives",
        ],
        "safety": "safe",
    },
    {
        "id": "xcode_ios_support",
        "group": "Desarrollo",
        "name": "Xcode: Soporte de dispositivos iOS",
        "icon": "smartphone",
        "description": (
            "Símbolos de depuración de versiones viejas de iOS. Ocupan mucho espacio; "
            "Xcode los vuelve a descargar solo si necesitás depurar en un iPhone."
        ),
        "path_patterns": [
            "~/Library/Developer/Xcode/iOS DeviceSupport",
            "~/Library/Developer/Xcode/watchOS DeviceSupport",
            "~/Library/Developer/Xcode/tvOS DeviceSupport",
        ],
        "safety": "caution",
    },
    {
        "id": "ios_simulators",
        "group": "Desarrollo",
        "name": "Cachés de simuladores iOS",
        "icon": "smartphone",
        "description": (
            "Cachés y datos temporales de los simuladores de iPhone/iPad de Xcode. "
            "No borra los simuladores, solo los datos temporales."
        ),
        "path_patterns": [
            "~/Library/Developer/CoreSimulator/Caches",
        ],
        "safety": "safe",
    },
    {
        "id": "homebrew_cache",
        "group": "Desarrollo",
        "name": "Caché de Homebrew",
        "icon": "coffee",
        "description": "Descargas de fórmulas ya instaladas. Se pueden borrar sin afectar nada.",
        "path_patterns": [
            "~/Library/Caches/Homebrew",
            "/opt/homebrew/var/cache",
        ],
        "safety": "safe",
    },
    {
        "id": "pip_cache",
        "group": "Desarrollo",
        "name": "Caché de pip (Python)",
        "icon": "terminal",
        "description": "Wheels y paquetes descargados por pip.",
        "path_patterns": [
            "~/Library/Caches/pip",
            "~/.cache/pip",
        ],
        "safety": "safe",
    },
    {
        "id": "npm_cache",
        "group": "Desarrollo",
        "name": "Caché de npm y yarn (Node)",
        "icon": "terminal",
        "description": "Paquetes descargados por npm/yarn/pnpm.",
        "path_patterns": [
            "~/.npm/_cacache",
            "~/Library/Caches/Yarn",
            "~/Library/pnpm/store",
        ],
        "safety": "safe",
    },
]


CATEGORIES_WINDOWS = [
    # ---------------- SISTEMA ----------------
    {
        "id": "windows_temp",
        "group": "Sistema",
        "name": "Archivos temporales",
        "icon": "sparkles",
        "description": (
            "Carpeta %TEMP% del usuario. Contiene archivos que apps y el "
            "sistema usan a corto plazo. Es seguro borrarlos."
        ),
        "path_patterns": [
            "%TEMP%",
            "%LOCALAPPDATA%\\Temp",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_prefetch",
        "group": "Sistema",
        "name": "Prefetch",
        "icon": "sparkles",
        "description": (
            "Datos que Windows guarda para acelerar el arranque de programas. "
            "Se regeneran solos, pero borrarlos ralentiza levemente los primeros "
            "usos. Requiere permisos de admin."
        ),
        "path_patterns": ["%WINDIR%\\Prefetch"],
        "safety": "caution",
    },
    {
        "id": "windows_thumb_cache",
        "group": "Sistema",
        "name": "Caché de miniaturas del Explorador",
        "icon": "image",
        "description": (
            "Miniaturas que el Explorador de archivos genera. Se regeneran."
        ),
        "path_patterns": [
            "%LOCALAPPDATA%\\Microsoft\\Windows\\Explorer\\thumbcache_*.db",
            "%LOCALAPPDATA%\\Microsoft\\Windows\\Explorer\\iconcache_*.db",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_recycle_bin",
        "group": "Sistema",
        "name": "Papelera de reciclaje",
        "icon": "trash",
        "description": (
            "Vacía la Papelera de reciclaje del usuario actual."
        ),
        "path_patterns": [
            # Cada usuario tiene su carpeta bajo su SID — el * matchea
            "C:\\$Recycle.Bin\\*",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_error_reports",
        "group": "Sistema",
        "name": "Informes de errores de Windows",
        "icon": "alert-triangle",
        "description": (
            "WER (Windows Error Reporting) — reportes que Windows guarda "
            "cuando algo se cierra inesperadamente."
        ),
        "path_patterns": [
            "%LOCALAPPDATA%\\Microsoft\\Windows\\WER",
            "%PROGRAMDATA%\\Microsoft\\Windows\\WER",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_delivery_optimization",
        "group": "Sistema",
        "name": "Caché de Windows Update",
        "icon": "file-text",
        "description": (
            "Archivos descargados por Windows Update / Delivery Optimization "
            "que ya se instalaron. Requiere permisos de admin."
        ),
        "path_patterns": [
            "%WINDIR%\\SoftwareDistribution\\Download",
        ],
        "safety": "caution",
    },

    # ---------------- NAVEGADORES ----------------
    {
        "id": "windows_browser_chrome",
        "group": "Navegadores",
        "name": "Caché de Google Chrome",
        "icon": "globe",
        "description": (
            "Datos temporales de páginas visitadas en Chrome. Cerrá el "
            "navegador antes de limpiar."
        ),
        "path_patterns": [
            "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Cache",
            "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Code Cache",
            "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\GPUCache",
            "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Service Worker\\CacheStorage",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_browser_edge",
        "group": "Navegadores",
        "name": "Caché de Microsoft Edge",
        "icon": "globe",
        "description": (
            "Datos temporales de páginas visitadas en Edge. Cerrá el navegador antes de limpiar."
        ),
        "path_patterns": [
            "%LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\Default\\Cache",
            "%LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\Default\\Code Cache",
            "%LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\Default\\GPUCache",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_browser_firefox",
        "group": "Navegadores",
        "name": "Caché de Firefox",
        "icon": "globe",
        "description": (
            "Datos temporales de páginas visitadas en Firefox. Cerrá el navegador antes de limpiar."
        ),
        "path_patterns": [
            "%APPDATA%\\Mozilla\\Firefox\\Profiles\\*\\cache2",
            "%APPDATA%\\Mozilla\\Firefox\\Profiles\\*\\startupCache",
            "%LOCALAPPDATA%\\Mozilla\\Firefox\\Profiles\\*\\cache2",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_browser_brave",
        "group": "Navegadores",
        "name": "Caché de Brave",
        "icon": "globe",
        "description": (
            "Datos temporales de páginas visitadas en Brave. Cerrá el navegador antes de limpiar."
        ),
        "path_patterns": [
            "%LOCALAPPDATA%\\BraveSoftware\\Brave-Browser\\User Data\\Default\\Cache",
            "%LOCALAPPDATA%\\BraveSoftware\\Brave-Browser\\User Data\\Default\\Code Cache",
            "%LOCALAPPDATA%\\BraveSoftware\\Brave-Browser\\User Data\\Default\\GPUCache",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_browser_opera",
        "group": "Navegadores",
        "name": "Caché de Opera",
        "icon": "globe",
        "description": "Datos temporales de páginas visitadas en Opera. Cerrá el navegador antes de limpiar.",
        "path_patterns": [
            "%APPDATA%\\Opera Software\\Opera Stable\\Cache",
            "%APPDATA%\\Opera Software\\Opera Stable\\Code Cache",
        ],
        "safety": "safe",
    },

    # ---------------- RESTOS DE PROGRAMAS ----------------
    {
        "id": "windows_adobe_leftovers",
        "group": "Restos de programas",
        "name": "Restos de Adobe",
        "icon": "palette",
        "description": (
            "Cachés, logs y datos que Adobe deja incluso después de actualizar "
            "o desinstalar Photoshop, Acrobat, Creative Cloud, Premiere, etc. "
            "Cerrá cualquier app de Adobe antes de limpiar."
        ),
        "path_patterns": [
            "%APPDATA%\\Adobe\\Common\\Media Cache",
            "%APPDATA%\\Adobe\\Common\\Media Cache Files",
            "%LOCALAPPDATA%\\Adobe",
            "%APPDATA%\\Adobe\\OOBE\\Cache",
            "%APPDATA%\\Adobe\\Bridge*\\Cache",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_office_leftovers",
        "group": "Restos de programas",
        "name": "Restos de Microsoft Office",
        "icon": "file-text",
        "description": (
            "Cachés y datos temporales de Word, Excel, PowerPoint, Outlook, Teams."
        ),
        "path_patterns": [
            "%APPDATA%\\Microsoft\\Office\\Recent",
            "%LOCALAPPDATA%\\Microsoft\\Office\\16.0\\OfficeFileCache",
            "%APPDATA%\\Microsoft\\Teams\\Cache",
            "%APPDATA%\\Microsoft\\Teams\\Code Cache",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_app_updaters",
        "group": "Restos de programas",
        "name": "Instaladores y actualizadores viejos",
        "icon": "box",
        "description": (
            "Archivos que quedan tras actualizar apps: Zoom, Slack, Spotify, Discord, etc."
        ),
        "path_patterns": [
            "%APPDATA%\\Zoom\\bin",
            "%LOCALAPPDATA%\\slack\\packages",
            "%APPDATA%\\Spotify\\Storage",
            "%APPDATA%\\discord\\Cache",
            "%APPDATA%\\discord\\Code Cache",
        ],
        "safety": "safe",
    },
    # -------- Caches de apps de video (SUELEN OCUPAR MUCHOS GB) --------
    {
        "id": "windows_capcut_cache",
        "group": "Restos de programas",
        "name": "Caché de CapCut (editor de video)",
        "icon": "palette",
        "description": (
            "Renders, previews y cachés temporales de CapCut. Se regeneran al abrir "
            "cada proyecto. Suele ocupar decenas de GB en usuarios activos."
        ),
        "path_patterns": [
            "%LOCALAPPDATA%\\CapCut\\User Data\\*\\Cache",
            "%LOCALAPPDATA%\\CapCut\\User Data\\*\\Code Cache",
            "%LOCALAPPDATA%\\CapCut\\User Data\\*\\CachedFiles",
            "%LOCALAPPDATA%\\CapCut\\User Data\\*\\DraftCache",
            "%LOCALAPPDATA%\\CapCut\\User Data\\*\\preview_files",
            "%LOCALAPPDATA%\\CapCut\\User Data\\*\\CacheStorage",
            "%LOCALAPPDATA%\\CapCut\\User Data\\*\\GPUCache",
            "%LOCALAPPDATA%\\CapCut\\Live\\CacheData",
            "%LOCALAPPDATA%\\CapCut\\Apps\\*\\Cache",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_davinci_cache",
        "group": "Restos de programas",
        "name": "Caché de DaVinci Resolve",
        "icon": "palette",
        "description": (
            "Cachés y previews de DaVinci Resolve. Se regeneran al abrir proyectos. "
            "Cerrá Resolve antes de limpiar."
        ),
        "path_patterns": [
            "%LOCALAPPDATA%\\Blackmagic Design\\DaVinci Resolve\\CacheClip",
            "%APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Cache",
            "%APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Logs",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_premiere_cache",
        "group": "Restos de programas",
        "name": "Media Cache de Adobe Premiere / After Effects",
        "icon": "palette",
        "description": (
            "Cache de medios de Premiere Pro y After Effects. Se regenera al reabrir "
            "los proyectos. Puede ocupar GB si editás mucho."
        ),
        "path_patterns": [
            "%USERPROFILE%\\Documents\\Adobe\\Premiere Pro\\*\\Media Cache Files",
            "%USERPROFILE%\\Documents\\Adobe\\Premiere Pro\\*\\Media Cache",
            "%USERPROFILE%\\Documents\\Adobe\\Common\\Media Cache Files",
            "%USERPROFILE%\\Documents\\Adobe\\Common\\Media Cache",
            "%USERPROFILE%\\Documents\\Adobe\\After Effects*\\Disk Cache*",
            "%APPDATA%\\Adobe\\Common\\Media Cache Files",
        ],
        "safety": "safe",
    },
    # -------- Comunicación --------
    {
        "id": "windows_teams_cache",
        "group": "Restos de programas",
        "name": "Caché de Microsoft Teams",
        "icon": "file-text",
        "description": "Cache de mensajes/imágenes de Teams. Cerrá Teams antes de limpiar.",
        "path_patterns": [
            "%APPDATA%\\Microsoft\\Teams\\Cache",
            "%APPDATA%\\Microsoft\\Teams\\Code Cache",
            "%APPDATA%\\Microsoft\\Teams\\GPUCache",
            "%APPDATA%\\Microsoft\\Teams\\Service Worker\\CacheStorage",
            "%LOCALAPPDATA%\\Packages\\MSTeams_*\\LocalCache",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_slack_cache",
        "group": "Restos de programas",
        "name": "Caché de Slack",
        "icon": "file-text",
        "description": "Cache de canales/imágenes de Slack. Cerrá Slack antes de limpiar.",
        "path_patterns": [
            "%APPDATA%\\Slack\\Cache",
            "%APPDATA%\\Slack\\Code Cache",
            "%APPDATA%\\Slack\\GPUCache",
            "%APPDATA%\\Slack\\Service Worker\\CacheStorage",
        ],
        "safety": "safe",
    },
    # -------- Cloud storage caches --------
    {
        "id": "windows_dropbox_cache",
        "group": "Restos de programas",
        "name": "Caché de Dropbox",
        "icon": "hard-drive",
        "description": (
            "Cache temporal de descarga de Dropbox. Se regenera. Cerrá Dropbox si querés "
            "limpiar todo."
        ),
        "path_patterns": [
            "%LOCALAPPDATA%\\Dropbox\\cache",
            "%LOCALAPPDATA%\\Dropbox\\l\\storage",
            "%LOCALAPPDATA%\\Dropbox\\instance*\\logs",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_google_drive_cache",
        "group": "Restos de programas",
        "name": "Caché de Google Drive (Streaming)",
        "icon": "hard-drive",
        "description": (
            "Archivos en caché de Google Drive Streaming (offline). Al limpiar podés perder "
            "acceso rápido a archivos hasta que se re-descarguen."
        ),
        "path_patterns": [
            "%LOCALAPPDATA%\\Google\\DriveFS\\Logs",
        ],
        "safety": "caution",
    },
    # -------- Dev tools --------
    {
        "id": "windows_vscode_cache",
        "group": "Desarrollo",
        "name": "VS Code: caches y logs",
        "icon": "code",
        "description": "Caches y logs de VS Code. Se regeneran, tu configuración queda intacta.",
        "path_patterns": [
            "%APPDATA%\\Code\\Cache",
            "%APPDATA%\\Code\\Code Cache",
            "%APPDATA%\\Code\\GPUCache",
            "%APPDATA%\\Code\\logs",
            "%APPDATA%\\Code\\CachedData",
            "%APPDATA%\\Code\\Service Worker\\CacheStorage",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_docker_logs",
        "group": "Desarrollo",
        "name": "Docker Desktop: logs",
        "icon": "code",
        "description": "Logs de Docker Desktop. No toca las imágenes ni containers.",
        "path_patterns": [
            "%LOCALAPPDATA%\\Docker\\log",
            "%APPDATA%\\Docker\\log",
        ],
        "safety": "safe",
    },
    # -------- Streaming --------
    {
        "id": "windows_obs_cache",
        "group": "Restos de programas",
        "name": "Logs de OBS Studio",
        "icon": "file-text",
        "description": (
            "Logs de OBS. NO toca tus grabaciones (esas están en Videos por default)."
        ),
        "path_patterns": [
            "%APPDATA%\\obs-studio\\logs",
            "%APPDATA%\\obs-studio\\crashes",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_old_downloads",
        "group": "Restos de programas",
        "name": "Instaladores .exe / .msi viejos en Descargas",
        "icon": "hard-drive",
        "description": (
            "Archivos .exe, .msi y .zip en Descargas de más de 30 días. "
            "Revisá antes de borrar por si hay algo importante."
        ),
        "path_patterns": [
            "%USERPROFILE%\\Downloads\\*.exe",
            "%USERPROFILE%\\Downloads\\*.msi",
            "%USERPROFILE%\\Downloads\\*.zip",
        ],
        "safety": "caution",
        "min_age_days": 30,
    },

    # ---------------- DESARROLLO ----------------
    {
        "id": "windows_dev_npm",
        "group": "Desarrollo",
        "name": "Caché de npm y yarn (Node)",
        "icon": "terminal",
        "description": "Paquetes descargados por npm/yarn/pnpm.",
        "path_patterns": [
            "%APPDATA%\\npm-cache",
            "%LOCALAPPDATA%\\Yarn\\Cache",
            "%LOCALAPPDATA%\\pnpm\\store",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_dev_pip",
        "group": "Desarrollo",
        "name": "Caché de pip (Python)",
        "icon": "terminal",
        "description": "Wheels y paquetes descargados por pip.",
        "path_patterns": [
            "%LOCALAPPDATA%\\pip\\Cache",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_dev_nuget",
        "group": "Desarrollo",
        "name": "Caché de NuGet (.NET)",
        "icon": "terminal",
        "description": "Paquetes descargados por NuGet.",
        "path_patterns": [
            "%USERPROFILE%\\.nuget\\packages",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_dev_vs",
        "group": "Desarrollo",
        "name": "Visual Studio: caché de componentes",
        "icon": "hammer",
        "description": (
            "ComponentModelCache de Visual Studio. Se regenera al abrir VS. "
            "Útil borrarlo si VS anda lento."
        ),
        "path_patterns": [
            "%LOCALAPPDATA%\\Microsoft\\VisualStudio\\*\\ComponentModelCache",
        ],
        "safety": "safe",
    },
    {
        "id": "windows_dev_dotnet",
        "group": "Desarrollo",
        "name": ".NET package cache",
        "icon": "terminal",
        "description": "Cachés de restore de .NET tools.",
        "path_patterns": [
            "%LOCALAPPDATA%\\NuGet\\v3-cache",
            "%LOCALAPPDATA%\\Temp\\NuGetScratch",
        ],
        "safety": "safe",
    },
]


def get_categories() -> list:
    """Devuelve las categorías apropiadas para el sistema operativo actual."""
    if is_mac():
        return CATEGORIES_MAC
    if is_windows():
        return CATEGORIES_WINDOWS
    return []


def get_groups(categories: list) -> list:
    """
    Devuelve la lista de grupos únicos en el orden en que aparecen.
    """
    seen = []
    for c in categories:
        g = c.get("group", "Otros")
        if g not in seen:
            seen.append(g)
    return seen
