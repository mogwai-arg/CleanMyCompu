"""
CleanMyCompu — GUI principal.
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import Qt, QObject, QThread, Signal, QSize, QSettings
from PySide6.QtGui import QFont, QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QCheckBox, QScrollArea, QFrame, QListWidget,
    QListWidgetItem, QProgressBar, QStatusBar, QStackedWidget, QDialog,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QMessageBox, QLineEdit,
)
from PySide6.QtGui import QColor

from targets import get_categories
from scanner import scan_category, get_paths_for_category
from cleaner import clean_paths
from ui_theme import Spacing, Type, Colors, build_stylesheet, is_dark_mode
from dialogs import (ConfirmCleanDialog, ConfirmDialog, InfoDialog,
                     ProgressDialog, RunningProcessesDialog)
from icons import make_icon_pixmap, make_logo_pixmap
import duplicates
import uninstaller
import large_files
import startup_items
import memory_clean
import software_updater
import updater
import stats
import permissions
import performance
from confetti import Confetti
from notifications import notify
from platform_helpers import is_windows, is_mac
from PySide6.QtCore import QTimer


# ============================================================
# Utilidades
# ============================================================

def human_bytes(n) -> str:
    if n is None:
        return "—"
    n = float(n)
    if n < 1024:
        return f"{int(n)} B"
    for unit in ("KB", "MB", "GB", "TB"):
        n /= 1024
        if n < 1024:
            return f"{n:.1f} {unit}"
    return f"{n:.1f} PB"


def storage_summary() -> str:
    try:
        total, _used, free = shutil.disk_usage("/")
        return f"{human_bytes(free)} libres de {human_bytes(total)}"
    except OSError:
        return ""


def icon_color() -> str:
    return Colors.TEXT_DARK if is_dark_mode() else Colors.TEXT_LIGHT


def icon_secondary_color() -> str:
    return Colors.TEXT_SEC_DARK if is_dark_mode() else Colors.TEXT_SEC_LIGHT


def sidebar_selected_icon_color() -> str:
    """
    Color del ícono cuando el item del sidebar está seleccionado.
    El fondo del item seleccionado es oscuro en light-mode y claro en dark-mode,
    entonces el ícono va invertido para tener contraste.
    """
    return "#FFFFFF" if not is_dark_mode() else "#1C1C1E"


def sidebar_item_icon(name: str) -> QIcon:
    """QIcon con dos modos: Normal (color texto) + Selected (invertido)."""
    icon = QIcon()
    icon.addPixmap(make_icon_pixmap(name, 18, icon_color()), QIcon.Normal)
    icon.addPixmap(make_icon_pixmap(name, 18, sidebar_selected_icon_color()),
                   QIcon.Selected)
    return icon


def format_atime(ts: float) -> str:
    try:
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return "?"


# ============================================================
# Secciones del sidebar
# ============================================================

SECTIONS = [
    {"key": "Smart Scan", "icon": "stethoscope", "menu_group": "ANÁLISIS",
     "desc": "Analizá tu compu y explorá cada módulo para liberar espacio."},

    {"key": "Sistema", "icon": "sparkles", "menu_group": "CATEGORÍAS",
     "desc": "Cachés, logs y otros archivos temporales que el sistema y las apps dejan atrás."},
    {"key": "Navegadores", "icon": "globe", "menu_group": "CATEGORÍAS",
     "desc": "Cachés de Chrome, Safari, Firefox, Edge y Brave. Cerrá el navegador antes de limpiar."},
    {"key": "Restos de programas", "icon": "palette", "menu_group": "CATEGORÍAS",
     "desc": "Archivos que dejaron programas viejos, actualizados o desinstalados."},
    {"key": "Desarrollo", "icon": "code", "menu_group": "CATEGORÍAS",
     "desc": "Cachés de herramientas: Xcode, Homebrew, pip, npm, simuladores iOS."},

    {"key": "Duplicados", "icon": "copy", "menu_group": "HERRAMIENTAS",
     "desc": "Encuentra archivos idénticos en Descargas, Documentos, Escritorio, Imágenes y Videos."},
    {"key": "Desinstalador", "icon": "app-window", "menu_group": "HERRAMIENTAS",
     "desc": "Desinstala apps y borra también los rastros que dejan en ~/Library."},
    {"key": "Archivos grandes", "icon": "hard-drive", "menu_group": "HERRAMIENTAS",
     "desc": "Archivos de más de 100 MB que no abrís hace 6+ meses. Revisá antes de borrar."},
    {"key": "Elementos de inicio", "icon": "power", "menu_group": "HERRAMIENTAS",
     "desc": "Agentes de inicio del usuario que se ejecutan al arrancar la compu."},
    {"key": "Rendimiento", "icon": "cpu", "menu_group": "HERRAMIENTAS",
     "desc": "Suspender apps que consumen RAM para liberar memoria virtual sin cerrarlas."},
    {"key": "Actualizador", "icon": "download", "menu_group": "HERRAMIENTAS",
     "desc": "Verifica y actualiza apps y paquetes instalados via Homebrew.",
     "platform": "darwin"},
    {"key": "Memoria", "icon": "cpu", "menu_group": "HERRAMIENTAS",
     "desc": "Libera RAM inactiva de macOS con un clic. Útil si sentís la Mac lenta.",
     "platform": "darwin"},
    {"key": "Estadísticas", "icon": "clock", "menu_group": "HERRAMIENTAS",
     "desc": "Mira cuánto espacio liberaste con CleanMyCompu a lo largo del tiempo."},
    {"key": "Permisos", "icon": "info", "menu_group": "HERRAMIENTAS",
     "desc": "Configurá el acceso al disco para que macOS no vuelva a preguntar en cada carpeta.",
     "platform": "darwin"},
]

# Filtrar por plataforma actual — items sin campo 'platform' están en ambos
SECTIONS = [
    s for s in SECTIONS
    if not s.get("platform") or s["platform"] == sys.platform.rstrip("32")
]

SECTIONS_BY_KEY = {s["key"]: s for s in SECTIONS}


# ============================================================
# Onboarding — tip que se muestra la primera vez que abrís cada sección
# ============================================================

ONBOARDING = {
    "Smart Scan": (
        "Este es tu panel general",
        "Cada tarjeta representa un módulo. Podés hacer clic en 'Analizar todo' para "
        "escanear las 4 categorías principales de una, o entrar a cada módulo por separado.",
    ),
    "Sistema": (
        "Cachés, logs y basura del sistema",
        "Todo lo que ves acá es 100% seguro de borrar: las apps recrean estos archivos "
        "cuando los necesitan. Presioná 'Analizar' y después marcá qué querés limpiar.",
    ),
    "Navegadores": (
        "Cachés de tus navegadores",
        "Cerrá Chrome, Safari, Firefox, Edge y Brave antes de limpiar para evitar errores. "
        "Se borran solo cachés, no tu historial ni tus contraseñas.",
    ),
    "Restos de programas": (
        "Rastros de programas viejos",
        "Adobe, Office, actualizadores de apps que ya no usás. Suelen ocupar GBs enteros. "
        "Los 'restos de apps desinstaladas' son detectados heurísticamente — revisá antes de borrar.",
    ),
    "Desarrollo": (
        "Cachés de herramientas de dev",
        "Xcode, Homebrew, npm, pip. Si desarrollás, estas cachés se regeneran al usar cada "
        "herramienta. Ojo con 'Soporte de dispositivos iOS' — se re-descarga si volvés a conectar el iPhone en Xcode.",
    ),
    "Duplicados": (
        "Archivos idénticos por hash",
        "Escanea Descargas, Documentos, Escritorio, Imágenes y Videos. La primera copia queda "
        "sin marcar (se conserva); las demás se marcan para borrar. Revisá cada grupo antes de confirmar.",
    ),
    "Desinstalador": (
        "Desinstala apps y sus rastros",
        "Encuentra la app + todos los archivos que dejó en ~/Library. Las que no abrís hace "
        "6+ meses (según Spotlight) aparecen primero, marcadas en naranja como 'recomendadas para desinstalar'.",
    ),
    "Archivos grandes": (
        "Archivos grandes olvidados",
        "Muestra archivos de +100 MB que no abrís hace 6+ meses. Los checkboxes vienen sin marcar "
        "porque acá tenés que revisar uno por uno: puede haber cosas importantes.",
    ),
    "Elementos de inicio": (
        "Agentes que arrancan con tu Mac",
        "Los marcados con badge naranja 'RECOMENDADO DESACTIVAR' son bloatware conocido "
        "(Adobe schedulers, Google Updater, etc.) que podés apagar sin miedo. Desactivar es "
        "reversible; quitar es permanente.",
    ),
    "Actualizador": (
        "Actualiza paquetes de Homebrew",
        "Lista formulae y casks instalados via brew que tienen updates disponibles. "
        "Podés actualizar todos de una o seleccionar específicos. Requiere Homebrew instalado.",
    ),
    "Memoria": (
        "Liberá RAM inactiva",
        "macOS retiene páginas de memoria en caché (Inactive/Compressed) incluso cuando las "
        "apps ya no las necesitan. Un clic ejecuta `purge` que las libera. macOS te pedirá "
        "la contraseña (requiere admin).",
    ),
    "Estadísticas": (
        "Tu impacto acumulado",
        "Cada limpieza que hacés queda registrada en ~/.cleanmycompu/stats.json. "
        "Acá ves cuánto liberaste en total y en los últimos 30 días, con desglose "
        "por categoría.",
    ),
    "Permisos": (
        "¿Cansado de que macOS pida permiso por cada carpeta?",
        "Con un clic te llevo al panel donde le podés dar 'Acceso completo al disco' "
        "a CleanMyCompu. Después de eso, macOS deja de preguntar y los scans son mucho más rápidos.",
    ),
    "Rendimiento": (
        "Liberá memoria suspendiendo apps",
        "Lista los procesos que más RAM están consumiendo. Podés SUSPENDERLOS "
        "(pausar temporalmente sin cerrarlos, sin perder trabajo) para liberar "
        "memoria virtual cuando la compu se queda lenta. Después los reanudás "
        "cuando quieras y vuelven a donde estaban.",
    ),
}


class OnboardingBanner(QFrame):
    """Banner que aparece la primera vez que entrás a una sección."""
    dismissed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("onboarding-banner")
        h = QHBoxLayout(self)
        h.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.MD, Spacing.MD)
        h.setSpacing(Spacing.MD)

        self.icon_lbl = QLabel()
        # Ícono con el color del texto (regla: cero azul en la UI)
        self.icon_lbl.setPixmap(make_icon_pixmap("info", 20, icon_color()))
        self.icon_lbl.setFixedSize(24, 24)
        self.icon_lbl.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        h.addWidget(self.icon_lbl)

        col = QVBoxLayout()
        col.setSpacing(2)
        self.title_lbl = QLabel("")
        self.title_lbl.setObjectName("onboarding-title")
        self.body_lbl = QLabel("")
        self.body_lbl.setObjectName("onboarding-body")
        self.body_lbl.setWordWrap(True)
        col.addWidget(self.title_lbl)
        col.addWidget(self.body_lbl)
        h.addLayout(col, stretch=1)

        dismiss = QPushButton("Entendido")
        dismiss.setProperty("role", "secondary")
        dismiss.clicked.connect(self._dismiss)
        h.addWidget(dismiss, alignment=Qt.AlignTop)

        self.hide()

    def show_tip(self, title: str, body: str):
        self.title_lbl.setText(title)
        self.body_lbl.setText(body)
        self.show()

    def _dismiss(self):
        self.hide()
        self.dismissed.emit()


# ============================================================
# Workers
# ============================================================

class ScanWorker(QObject):
    category_scanned = Signal(dict)
    detail = Signal(str)
    finished = Signal()

    def __init__(self, categories):
        super().__init__()
        self.categories = categories

    def run(self):
        for cat in self.categories:
            self.detail.emit(f"Escaneando {cat['name']}…")
            self.category_scanned.emit(scan_category(cat))
        self.finished.emit()


class CleanWorker(QObject):
    progress = Signal(str)
    category_started = Signal(str)
    category_done = Signal(str, object)
    finished = Signal(object)

    def __init__(self, categories_to_clean):
        super().__init__()
        self.categories = categories_to_clean

    def run(self):
        total = 0
        for cat in self.categories:
            self.category_started.emit(cat["name"])
            paths = get_paths_for_category(cat)
            freed = clean_paths(paths, mode="permanent",
                                progress=lambda m: self.progress.emit(m))
            total += freed
            self.category_done.emit(cat["id"], freed)
        self.finished.emit(total)


class DuplicatesWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)

    def run(self):
        try:
            groups = duplicates.find_duplicates(
                on_progress=lambda m: self.progress.emit(m))
        except Exception as e:
            self.progress.emit(f"Error: {e}")
            groups = []
        self.finished.emit(groups)


class UninstallerWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)

    def run(self):
        self.progress.emit("Buscando apps en /Applications…")
        try:
            apps = uninstaller.list_installed_apps()
        except Exception:
            apps = []
        self.finished.emit(apps)


class LargeFilesWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)

    def run(self):
        try:
            files = large_files.find_large_files(
                on_progress=lambda m: self.progress.emit(m))
        except Exception as e:
            self.progress.emit(f"Error: {e}")
            files = []
        self.finished.emit(files)


class SoftwareUpdaterScanWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)  # list[dict]

    def run(self):
        self.progress.emit("Consultando Homebrew…")
        packages = software_updater.list_outdated()
        self.finished.emit(packages)


class SoftwareUpgradeWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)  # dict {success, output}

    def __init__(self, package_names=None):
        super().__init__()
        self.package_names = package_names  # None = todos

    def run(self):
        if self.package_names:
            result = software_updater.upgrade_specific(
                self.package_names,
                on_progress=lambda m: self.progress.emit(m))
        else:
            result = software_updater.upgrade_all(
                on_progress=lambda m: self.progress.emit(m))
        self.finished.emit(result)


class UpdateCheckWorker(QObject):
    """Consulta a la URL de manifest si hay una nueva versión de CleanMyCompu."""
    finished = Signal(object)  # dict o None

    def run(self):
        self.finished.emit(updater.check_for_update())


class ProcessListWorker(QObject):
    """Escanea procesos en background (list_processes puede tardar 1-2s)."""
    finished = Signal(object)  # list[dict]

    def run(self):
        try:
            procs = performance.list_processes(min_memory_mb=30)
        except Exception:
            procs = []
        self.finished.emit(procs)


# ============================================================
# Filas / tarjetas
# ============================================================

class CategoryRow(QFrame):
    checked_changed = Signal()

    def __init__(self, category: dict):
        super().__init__()
        self.setObjectName("category-row")
        self.category = category
        self.category_id = category["id"]
        self.scan_result: Optional[dict] = None

        h = QHBoxLayout(self)
        h.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        h.setSpacing(Spacing.LG)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(28, 28)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self._refresh_icon()
        h.addWidget(self.icon_label)

        col = QVBoxLayout()
        col.setSpacing(2)
        name = QLabel(category["name"])
        name.setObjectName("row-name")
        desc = QLabel(category.get("description", ""))
        desc.setObjectName("row-desc")
        desc.setWordWrap(True)
        col.addWidget(name)
        col.addWidget(desc)
        h.addLayout(col, stretch=1)

        self.size_label = QLabel("—")
        self.size_label.setObjectName("row-size")
        self.size_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.size_label.setMinimumWidth(84)
        h.addWidget(self.size_label)

        self.checkbox = QCheckBox()
        self.checkbox.setEnabled(False)
        self.checkbox.stateChanged.connect(lambda _: self.checked_changed.emit())
        h.addWidget(self.checkbox)
        self.setMinimumHeight(64)

    def _refresh_icon(self):
        self.icon_label.setPixmap(make_icon_pixmap(
            self.category.get("icon", "ghost"), size=22, color=icon_color()))

    def set_result(self, result: dict):
        self.scan_result = result
        if result["bytes"] == 0:
            self.size_label.setText("vacío")
            self.size_label.setObjectName("row-empty")
            self.checkbox.setChecked(False)
            self.checkbox.setEnabled(False)
        else:
            self.size_label.setText(human_bytes(result["bytes"]))
            self.size_label.setObjectName("row-size")
            self.checkbox.setEnabled(True)
            self.checkbox.setChecked(True)
        self._repolish_size()

    def mark_cleaned(self):
        if self.scan_result is not None:
            self.scan_result = {**self.scan_result, "bytes": 0, "file_count": 0}
        self.size_label.setText("vacío")
        self.size_label.setObjectName("row-empty")
        self.checkbox.setChecked(False)
        self.checkbox.setEnabled(False)
        self._repolish_size()

    def reset(self):
        self.scan_result = None
        self.size_label.setText("—")
        self.size_label.setObjectName("row-size")
        self.checkbox.setChecked(False)
        self.checkbox.setEnabled(False)
        self._repolish_size()

    def _repolish_size(self):
        self.size_label.style().unpolish(self.size_label)
        self.size_label.style().polish(self.size_label)

    def is_selected(self) -> bool:
        return (self.checkbox.isChecked() and self.checkbox.isEnabled()
                and self.scan_result is not None
                and self.scan_result["bytes"] > 0)


class DuplicateGroupRow(QFrame):
    changed = Signal()

    def __init__(self, group: list):
        super().__init__()
        self.setObjectName("category-row")
        self.group = group
        try:
            self.file_size = group[0].stat().st_size
        except OSError:
            self.file_size = 0

        v = QVBoxLayout(self)
        v.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        v.setSpacing(Spacing.SM)

        head = QHBoxLayout()
        head.setSpacing(Spacing.MD)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon_pixmap("copy", size=22, color=icon_color()))
        icon_lbl.setFixedSize(28, 28)
        head.addWidget(icon_lbl)

        col = QVBoxLayout()
        col.setSpacing(2)
        title = QLabel(f"{len(group)} copias idénticas")
        title.setObjectName("row-name")
        subtitle = QLabel(
            f"Cada archivo pesa {human_bytes(self.file_size)}. "
            f"Podés recuperar {human_bytes(self.file_size * (len(group)-1))} borrando duplicados.")
        subtitle.setObjectName("row-desc")
        subtitle.setWordWrap(True)
        col.addWidget(title)
        col.addWidget(subtitle)
        head.addLayout(col, stretch=1)
        v.addLayout(head)

        self.checkboxes = []
        for i, path in enumerate(group):
            row = QHBoxLayout()
            row.setContentsMargins(40, 0, 0, 0)
            cb = QCheckBox()
            cb.setChecked(i > 0)
            cb.stateChanged.connect(lambda _: self.changed.emit())
            self.checkboxes.append(cb)
            path_lbl = QLabel(str(path))
            path_lbl.setObjectName("row-desc")
            path_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            row.addWidget(cb)
            row.addWidget(path_lbl, stretch=1)
            v.addLayout(row)

    def selected_paths(self):
        return [p for p, cb in zip(self.group, self.checkboxes) if cb.isChecked()]

    def bytes_to_free(self) -> int:
        return self.file_size * sum(1 for cb in self.checkboxes if cb.isChecked())


class AppRow(QFrame):
    """Fila del desinstalador: una app instalada."""
    uninstall_requested = Signal(dict)
    ignore_recommendation = Signal(str)  # bundle_id

    def __init__(self, app: dict):
        super().__init__()
        # Highlight ambar si es recomendada para desinstalar
        self.setObjectName("row-recommended" if app.get("recommend") == "uninstall"
                           else "category-row")
        self.app = app

        h = QHBoxLayout(self)
        h.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        h.setSpacing(Spacing.LG)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon_pixmap("app-window", size=22, color=icon_color()))
        icon_lbl.setFixedSize(28, 28)
        h.addWidget(icon_lbl)

        col = QVBoxLayout()
        col.setSpacing(3)
        # Nombre + badge de recomendación en la misma fila
        name_row = QHBoxLayout()
        name_row.setSpacing(Spacing.SM)
        name_row.setContentsMargins(0, 0, 0, 0)
        name = QLabel(app["name"])
        name.setObjectName("row-name")
        name_row.addWidget(name)
        if app.get("recommend") == "uninstall":
            badge = QLabel("RECOMENDADO DESINSTALAR")
            badge.setProperty("role", "badge-warn")
            name_row.addWidget(badge)
        name_row.addStretch(1)
        col.addLayout(name_row)

        # Descripción / bundle ID
        desc_text = app["bundle_id"]
        desc = QLabel(desc_text)
        desc.setObjectName("row-desc")
        col.addWidget(desc)

        # Motivo (si hay recomendación) + botón "No sugerir más"
        if app.get("recommend") == "uninstall":
            reason_row = QHBoxLayout()
            reason_row.setSpacing(Spacing.SM)
            reason_row.setContentsMargins(0, 0, 0, 0)
            reason = QLabel(app.get("reason", ""))
            reason.setProperty("role", "reason")
            reason.setWordWrap(True)
            reason_row.addWidget(reason, stretch=1)
            ignore_btn = QPushButton("No sugerir más")
            ignore_btn.setProperty("role", "link")
            ignore_btn.setCursor(Qt.PointingHandCursor)
            ignore_btn.clicked.connect(
                lambda: self.ignore_recommendation.emit(self.app["bundle_id"]))
            reason_row.addWidget(ignore_btn)
            col.addLayout(reason_row)

        h.addLayout(col, stretch=1)

        size = QLabel(human_bytes(app["size"]))
        size.setObjectName("row-size")
        size.setMinimumWidth(80)
        size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(size)

        btn = QPushButton("Desinstalar…")
        btn.setProperty("role", "secondary")
        btn.clicked.connect(lambda: self.uninstall_requested.emit(self.app))
        h.addWidget(btn)

        self.setMinimumHeight(64)


class LargeFileRow(QFrame):
    """Fila de archivos grandes olvidados."""
    changed = Signal()

    def __init__(self, item: dict):
        super().__init__()
        self.setObjectName("category-row")
        self.item = item

        h = QHBoxLayout(self)
        h.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        h.setSpacing(Spacing.LG)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon_pixmap("hard-drive", size=22, color=icon_color()))
        icon_lbl.setFixedSize(28, 28)
        h.addWidget(icon_lbl)

        col = QVBoxLayout()
        col.setSpacing(2)
        name = QLabel(Path(item["path"]).name)
        name.setObjectName("row-name")
        desc = QLabel(f"{item['path'].parent}  ·  último acceso: {format_atime(item['atime'])}")
        desc.setObjectName("row-desc")
        desc.setWordWrap(True)
        desc.setTextInteractionFlags(Qt.TextSelectableByMouse)
        col.addWidget(name)
        col.addWidget(desc)
        h.addLayout(col, stretch=1)

        size = QLabel(human_bytes(item["size"]))
        size.setObjectName("row-size")
        size.setMinimumWidth(80)
        size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(size)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(False)  # opt-in — el usuario revisa
        self.checkbox.stateChanged.connect(lambda _: self.changed.emit())
        h.addWidget(self.checkbox)

        self.setMinimumHeight(64)

    def is_selected(self) -> bool:
        return self.checkbox.isChecked()


class StartupItemRow(QFrame):
    """Fila de un LaunchAgent."""
    toggled = Signal(dict, bool)
    removed = Signal(dict)
    ignore_recommendation = Signal(str)  # label

    def __init__(self, item: dict):
        super().__init__()
        # Highlight ambar si es recomendado desactivar y está activo
        highlight = (item.get("recommend") == "disable" and item.get("enabled"))
        self.setObjectName("row-recommended" if highlight else "category-row")
        self.item = item

        h = QHBoxLayout(self)
        h.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        h.setSpacing(Spacing.LG)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon_pixmap("power", size=22, color=icon_color()))
        icon_lbl.setFixedSize(28, 28)
        h.addWidget(icon_lbl)

        col = QVBoxLayout()
        col.setSpacing(3)

        # Nombre humano + badge (si aplica)
        name_row = QHBoxLayout()
        name_row.setSpacing(Spacing.SM)
        name_row.setContentsMargins(0, 0, 0, 0)
        name = QLabel(item["name"])
        name.setObjectName("row-name")
        name_row.addWidget(name)
        if highlight:
            badge = QLabel("RECOMENDADO DESACTIVAR")
            badge.setProperty("role", "badge-warn")
            name_row.addWidget(badge)
        name_row.addStretch(1)
        col.addLayout(name_row)

        # Descripción — qué hace realmente + tags de comportamiento
        parts = [item.get("friendly_desc", "")]
        tags = []
        if item.get("run_at_load"):
            tags.append("Arranca al inicio")
        if item.get("keep_alive"):
            tags.append("Se reinicia si se cierra")
        if tags:
            parts.append(" · ".join(tags))
        desc = QLabel(" · ".join(p for p in parts if p))
        desc.setObjectName("row-desc")
        desc.setWordWrap(True)
        col.addWidget(desc)

        # Motivo de la recomendación + botón "No sugerir más"
        if highlight:
            reason_row = QHBoxLayout()
            reason_row.setSpacing(Spacing.SM)
            reason_row.setContentsMargins(0, 0, 0, 0)
            reason = QLabel(item.get("reason", ""))
            reason.setProperty("role", "reason")
            reason.setWordWrap(True)
            reason_row.addWidget(reason, stretch=1)
            ignore_btn = QPushButton("No sugerir más")
            ignore_btn.setProperty("role", "link")
            ignore_btn.setCursor(Qt.PointingHandCursor)
            ignore_btn.clicked.connect(
                lambda: self.ignore_recommendation.emit(self.item["label"]))
            reason_row.addWidget(ignore_btn)
            col.addLayout(reason_row)

        # Label técnico (bundle ID) al final chiquito, para power users
        tech = QLabel(item["label"])
        tech.setObjectName("row-desc")
        tech.setStyleSheet("font-size: 10px; opacity: 0.6;")
        col.addWidget(tech)

        h.addLayout(col, stretch=1)

        status = QLabel("Activo" if item["enabled"] else "Desactivado")
        status.setObjectName("row-size" if item["enabled"] else "row-empty")
        status.setMinimumWidth(80)
        status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(status)
        self.status_label = status

        self.toggle_btn = QPushButton("Desactivar" if item["enabled"] else "Activar")
        self.toggle_btn.setProperty("role", "secondary")
        self.toggle_btn.clicked.connect(
            lambda: self.toggled.emit(self.item, not self.item["enabled"]))
        h.addWidget(self.toggle_btn)

        rm = QPushButton("Quitar")
        rm.setProperty("role", "destructive")
        rm.clicked.connect(lambda: self.removed.emit(self.item))
        h.addWidget(rm)

        self.setMinimumHeight(72)


class EmptyState(QFrame):
    """
    Estado vacío centrado con ícono grande + título + descripción + CTA opcional.
    Reemplaza los QLabels "planos" que quedaban muy pobres cuando no había datos.
    """
    def __init__(self, icon_name: str, title: str, body: str,
                 action_label: str = "", action_callback=None, parent=None):
        super().__init__(parent)
        self.setObjectName("empty-state")
        v = QVBoxLayout(self)
        v.setContentsMargins(Spacing.XXL, Spacing.XXXL, Spacing.XXL, Spacing.XXXL)
        v.setSpacing(Spacing.MD)

        # Ícono grande con círculo de fondo tenue (misma estética que InfoDialog)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon_pixmap(icon_name, size=48, color=icon_secondary_color()))
        icon_lbl.setFixedSize(80, 80)
        icon_lbl.setObjectName("empty-icon-bg")
        icon_lbl.setAlignment(Qt.AlignCenter)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(icon_lbl)
        row.addStretch(1)
        v.addLayout(row)

        # Título
        t = QLabel(title)
        t.setObjectName("empty-title")
        t.setAlignment(Qt.AlignCenter)
        t.setWordWrap(True)
        v.addWidget(t)

        # Body
        b = QLabel(body)
        b.setObjectName("empty-body")
        b.setAlignment(Qt.AlignCenter)
        b.setWordWrap(True)
        v.addWidget(b)

        # CTA opcional
        if action_label and action_callback is not None:
            btn_row = QHBoxLayout()
            btn_row.addStretch(1)
            btn = QPushButton(action_label)
            btn.setProperty("role", "positive")
            btn.clicked.connect(action_callback)
            btn_row.addWidget(btn)
            btn_row.addStretch(1)
            v.addSpacing(Spacing.MD)
            v.addLayout(btn_row)

    def set_body(self, text: str):
        # Encontrar el body label (segundo QLabel visible)
        labels = self.findChildren(QLabel)
        if len(labels) >= 3:
            labels[2].setText(text)

    # Alias compat con QLabel — así los setText() existentes siguen funcionando
    def setText(self, text: str):
        self.set_body(text)


class StorageBar(QWidget):
    """
    Mini barra visual + texto que muestra uso de disco.
    Verde si <70%, ámbar si 70-90%, rojo si >90%.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(Spacing.LG, Spacing.SM, Spacing.LG, Spacing.MD)
        v.setSpacing(Spacing.XS)

        # Track (fondo) + fill (relleno según %)
        self.track = QFrame()
        self.track.setObjectName("storage-bar-track")
        track_layout = QHBoxLayout(self.track)
        track_layout.setContentsMargins(0, 0, 0, 0)
        track_layout.setSpacing(0)
        self.fill = QFrame()
        self.fill.setObjectName("storage-bar-fill")
        track_layout.addWidget(self.fill)
        self.spacer = QWidget()
        track_layout.addWidget(self.spacer)
        v.addWidget(self.track)

        self.text = QLabel("")
        self.text.setObjectName("storage-text")
        self.text.setWordWrap(True)
        v.addWidget(self.text)

        # Indicador de update disponible (oculto por default). Texto corto y
        # sin wrap para que entre en una sola línea del sidebar.
        self.update_lbl = QLabel("")
        self.update_lbl.setObjectName("update-indicator")
        self.update_lbl.setWordWrap(False)
        self.update_lbl.setCursor(Qt.PointingHandCursor)
        self.update_lbl.setVisible(False)
        self.update_lbl.setToolTip("Clic para descargar la nueva versión")
        v.addWidget(self.update_lbl)

        self.refresh()

    def refresh(self):
        try:
            total, used, free = shutil.disk_usage("/")
        except OSError:
            self.text.setText("")
            return
        pct_used = used / max(1, total)
        # Ajustar el nombre según el nivel (colorea via QSS)
        if pct_used < 0.70:
            self.fill.setObjectName("storage-bar-fill")
        elif pct_used < 0.90:
            self.fill.setObjectName("storage-bar-fill-warn")
        else:
            self.fill.setObjectName("storage-bar-fill-full")
        # Re-polish para aplicar el nuevo objectName
        self.fill.style().unpolish(self.fill)
        self.fill.style().polish(self.fill)
        # Peso relativo en el layout
        self.track.layout().setStretch(0, max(1, int(pct_used * 1000)))
        self.track.layout().setStretch(1, max(1, int((1 - pct_used) * 1000)))
        self.text.setText(f"{human_bytes(free)} libres de {human_bytes(total)}")

    def show_update(self, version: str, url: str):
        self.update_lbl.setText(f"↑  Actualizar a v{version}")
        self.update_lbl.setVisible(True)
        self.update_lbl.mousePressEvent = lambda e: updater.open_download_page(url)


class ScrimOverlay(QWidget):
    """Fondo semi-transparente que oscurece la ventana detrás del ProgressDialog."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0, 0, 0, 100);")
        self.hide()

    def show_over(self):
        p = self.parentWidget()
        if p is None:
            return
        self.setGeometry(p.rect())
        self.raise_()
        self.show()


class ProcessRow(QFrame):
    """Fila de un proceso en la sección Rendimiento."""
    action_requested = Signal(int, str)  # (pid, action) — action: 'suspend' | 'resume' | 'kill'

    def __init__(self, proc: dict):
        super().__init__()
        self.setObjectName("category-row")
        self.proc = proc

        h = QHBoxLayout(self)
        h.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        h.setSpacing(Spacing.LG)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon_pixmap("cpu", size=22, color=icon_color()))
        icon_lbl.setFixedSize(28, 28)
        h.addWidget(icon_lbl)

        col = QVBoxLayout()
        col.setSpacing(2)
        name = QLabel(proc["name"])
        name.setObjectName("row-name")
        parts = [f"PID {proc['pid']}"]
        if proc.get("cpu_pct", 0) > 0:
            parts.append(f"{proc['cpu_pct']:.0f}% CPU")
        if proc.get("is_suspended"):
            parts.append("SUSPENDIDO")
        desc = QLabel("  ·  ".join(parts))
        desc.setObjectName("row-desc")
        col.addWidget(name)
        col.addWidget(desc)
        h.addLayout(col, stretch=1)

        mem = QLabel(f"{proc['memory_mb']:.0f} MB")
        mem.setObjectName("row-size")
        mem.setMinimumWidth(80)
        mem.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(mem)

        if proc.get("is_suspended"):
            resume_btn = QPushButton("Reanudar")
            resume_btn.setProperty("role", "positive")
            resume_btn.clicked.connect(lambda: self.action_requested.emit(proc["pid"], "resume"))
            h.addWidget(resume_btn)
        else:
            susp_btn = QPushButton("Suspender")
            susp_btn.setProperty("role", "secondary")
            susp_btn.clicked.connect(lambda: self.action_requested.emit(proc["pid"], "suspend"))
            h.addWidget(susp_btn)

        kill_btn = QPushButton("Cerrar")
        kill_btn.setProperty("role", "destructive")
        kill_btn.clicked.connect(lambda: self.action_requested.emit(proc["pid"], "kill"))
        h.addWidget(kill_btn)

        self.setMinimumHeight(64)


class OutdatedPackageRow(QFrame):
    """Fila de un paquete Homebrew con update disponible."""
    changed = Signal()

    def __init__(self, pkg: dict):
        super().__init__()
        self.setObjectName("category-row")
        self.pkg = pkg
        h = QHBoxLayout(self)
        h.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        h.setSpacing(Spacing.LG)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon_pixmap("arrow-up-circle", size=22,
                                            color=icon_color()))
        icon_lbl.setFixedSize(28, 28)
        h.addWidget(icon_lbl)

        col = QVBoxLayout()
        col.setSpacing(2)
        name = QLabel(f"{pkg['name']}   ({pkg['kind']})")
        name.setObjectName("row-name")
        desc = QLabel(f"{pkg['current']}  →  {pkg['latest']}")
        desc.setObjectName("row-desc")
        col.addWidget(name)
        col.addWidget(desc)
        h.addLayout(col, stretch=1)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.stateChanged.connect(lambda _: self.changed.emit())
        h.addWidget(self.checkbox)
        self.setMinimumHeight(60)

    def is_selected(self) -> bool:
        return self.checkbox.isChecked()


class MemoryStatBar(QFrame):
    """Barra horizontal segmentada que muestra uso de RAM."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("category-row")
        self._stats = None
        self.setMinimumHeight(140)

        v = QVBoxLayout(self)
        v.setContentsMargins(Spacing.XL, Spacing.LG, Spacing.XL, Spacing.LG)
        v.setSpacing(Spacing.MD)

        title = QLabel("Estado actual de la RAM")
        title.setObjectName("row-name")
        v.addWidget(title)

        # La "barra" es un QFrame con hijos que dibujamos con QSS
        self.bar_wrap = QWidget()
        self.bar_wrap.setFixedHeight(24)
        self.bar_layout = QHBoxLayout(self.bar_wrap)
        self.bar_layout.setContentsMargins(0, 0, 0, 0)
        self.bar_layout.setSpacing(2)
        v.addWidget(self.bar_wrap)

        self.legend = QLabel("Cargando…")
        self.legend.setObjectName("row-desc")
        self.legend.setWordWrap(True)
        v.addWidget(self.legend)

    def set_stats(self, stats: dict):
        self._stats = stats
        total = max(1, stats.get("total", 1))
        # Limpiar barra previa
        while self.bar_layout.count():
            it = self.bar_layout.takeAt(0)
            if it.widget():
                it.widget().setParent(None)
        # Segmentos: wired (rojo), active (naranja), compressed (violeta),
        # inactive (amarillo — liberable), free (verde)
        segments = [
            ("wired", stats.get("wired", 0), "#FF3B30"),
            ("active", stats.get("active", 0), "#FF9500"),
            ("compressed", stats.get("compressed", 0), "#AF52DE"),
            ("inactive", stats.get("inactive", 0), "#FFCC00"),
            ("free", stats.get("free", 0), "#34C759"),
        ]
        for name, val, color in segments:
            if val <= 0:
                continue
            seg = QFrame()
            seg.setStyleSheet(f"background:{color}; border-radius: 4px;")
            seg.setToolTip(f"{name}: {human_bytes(val)}")
            # weight proporcional
            self.bar_layout.addWidget(seg, stretch=max(1, int(val * 1000 / total)))

        used = stats.get("used", 0)
        free = stats.get("free", 0)
        inactive = stats.get("inactive", 0)
        parts = [
            f"En uso: {human_bytes(used)}",
            f"Libre: {human_bytes(free)}",
            f"Inactiva (liberable con 'purge'): {human_bytes(inactive)}",
            f"Total: {human_bytes(total)}",
        ]
        self.legend.setText("  ·  ".join(parts))


class DashboardCard(QFrame):
    """Tarjeta grande del dashboard."""
    clicked = Signal(str)

    def __init__(self, section: dict):
        super().__init__()
        self.setObjectName("dash-card")
        self.section_key = section["key"]
        self.section = section
        self.setCursor(Qt.PointingHandCursor)

        v = QVBoxLayout(self)
        v.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        v.setSpacing(Spacing.SM)

        head = QHBoxLayout()
        head.setSpacing(Spacing.MD)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon_pixmap(section["icon"], size=28, color=icon_color()))
        icon_lbl.setFixedSize(36, 36)
        head.addWidget(icon_lbl)
        head.addStretch(1)
        chev = QLabel()
        chev.setPixmap(make_icon_pixmap("chevron-right", size=18,
                                        color=Colors.TEXT_SEC_DARK if is_dark_mode()
                                        else Colors.TEXT_SEC_LIGHT))
        chev.setFixedSize(20, 20)
        head.addWidget(chev)
        v.addLayout(head)

        v.addSpacing(Spacing.XS)

        name = QLabel(section["key"])
        name.setObjectName("dash-card-name")
        v.addWidget(name)

        self.status_lbl = QLabel("Sin analizar")
        self.status_lbl.setObjectName("dash-card-status")
        self.status_lbl.setWordWrap(True)
        v.addWidget(self.status_lbl)

        self.setMinimumSize(220, 130)

        # Drop-shadow sutil siempre visible + más pronunciada en hover
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(8)
        self._shadow.setOffset(0, 2)
        self._shadow.setColor(QColor(0, 0, 0, 24))
        self.setGraphicsEffect(self._shadow)

    def enterEvent(self, event):
        self._shadow.setBlurRadius(20)
        self._shadow.setOffset(0, 6)
        self._shadow.setColor(QColor(0, 0, 0, 50))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._shadow.setBlurRadius(8)
        self._shadow.setOffset(0, 2)
        self._shadow.setColor(QColor(0, 0, 0, 24))
        super().leaveEvent(event)

    def set_status(self, text: str, highlight: bool = False):
        self.status_lbl.setText(text)
        self.status_lbl.setObjectName("dash-card-status-hl" if highlight
                                      else "dash-card-status")
        self.status_lbl.style().unpolish(self.status_lbl)
        self.status_lbl.style().polish(self.status_lbl)

    def mousePressEvent(self, event):
        self.clicked.emit(self.section_key)
        super().mousePressEvent(event)


# ============================================================
# MainWindow
# ============================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CleanMyCompu")
        self.resize(1080, 720)
        self.setMinimumSize(900, 600)

        self.categories = get_categories()
        self.scan_results = {}
        self.rows: dict[str, CategoryRow] = {}
        self.dup_rows: List[DuplicateGroupRow] = []
        self.app_rows: List[AppRow] = []
        self.large_rows: List[LargeFileRow] = []
        self.startup_rows: List[StartupItemRow] = []
        self.dashboard_cards: dict[str, DashboardCard] = {}
        self.current_section = "Smart Scan"
        self.thread = None
        self.worker = None
        self.progress_dialog: Optional[ProgressDialog] = None
        self._sidebar_lists = []

        # QSettings para persistir estado (ej. qué secciones ya vio el usuario)
        self.settings = QSettings("CleanMyCompu", "CleanMyCompu")

        def _load_set(key):
            v = self.settings.value(key, [])
            if isinstance(v, str):
                v = [v]
            return set(v or [])

        self.visited_sections = _load_set("visited_sections")
        self.ignored_startup_recs = _load_set("ignored_startup_recs")
        self.ignored_uninstall_recs = _load_set("ignored_uninstall_recs")

        self._build_ui()
        self._apply_theme()

    # ---- Construcción ----

    def _build_ui(self):
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_detail(), stretch=1)
        self.setCentralWidget(central)
        # Overlay que oscurece la ventana cuando hay un modal activo
        self.overlay = ScrimOverlay(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(f"Listo. CleanMyCompu v{updater.__version__}")
        # Selección inicial (después de que ya existan hero_title, stack, etc.)
        if self._sidebar_lists:
            self._sidebar_lists[0].setCurrentRow(0)
        # Chequear updates en background 2s después de abrir
        self._schedule_update_check()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "overlay") and self.overlay.isVisible():
            self.overlay.setGeometry(self.centralWidget().rect())

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)

        # Layout externo: scroll (expandible) + storage bar pinneado abajo
        outer = QVBoxLayout(sidebar)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Área scrollable interna con toda la navegación
        scroll = QScrollArea()
        scroll.setObjectName("sidebar-scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_content = QWidget()
        scroll_content.setObjectName("sidebar")  # hereda estilo de sidebar
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo + título
        head = QWidget()
        hh = QHBoxLayout(head)
        hh.setContentsMargins(Spacing.LG, Spacing.XL, Spacing.LG, Spacing.MD)
        hh.setSpacing(Spacing.XS)  # 4px — casi pegado
        logo = QLabel()
        if is_dark_mode():
            logo.setPixmap(make_logo_pixmap(size=32, bg="#F5F5F7", fg="#1C1C1E"))
        else:
            logo.setPixmap(make_logo_pixmap(size=32, bg="#1D1D1F", fg="#FFFFFF"))
        logo.setFixedSize(36, 36)
        logo.setAlignment(Qt.AlignCenter)
        hh.addWidget(logo)
        title = QLabel("CleanMyCompu")
        title.setObjectName("sidebar-title")
        title.setStyleSheet("padding: 0;")
        hh.addWidget(title, stretch=1)
        layout.addWidget(head)

        # Agrupar SECTIONS por menu_group
        groups_order = []
        by_group: dict[str, list] = {}
        for s in SECTIONS:
            g = s["menu_group"]
            if g not in by_group:
                by_group[g] = []
                groups_order.append(g)
            by_group[g].append(s)

        # Crear un QListWidget por grupo, con encabezado
        for g in groups_order:
            cap = QLabel(g)
            cap.setObjectName("sidebar-caption")
            layout.addWidget(cap)

            lst = QListWidget()
            lst.setObjectName("sidebar-list")
            lst.setFrameShape(QFrame.NoFrame)
            lst.setIconSize(QSize(18, 18))
            # nunca mostrar scrollbars: los items entran exactos
            lst.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            lst.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            lst.setSelectionMode(QListWidget.SingleSelection)
            for s in by_group[g]:
                it = QListWidgetItem(sidebar_item_icon(s["icon"]), f"  {s['key']}")
                it.setData(Qt.UserRole, s["key"])
                lst.addItem(it)
            # altura por item — usar sizeHint real para evitar clipping
            # (38px era muy justo con la nueva tipografía + iconos)
            lst.setUniformItemSizes(True)
            item_h = 42  # padding + texto + margin, con margen de seguridad
            lst.setFixedHeight(item_h * len(by_group[g]) + 6)
            lst.itemSelectionChanged.connect(
                lambda listw=lst: self._on_sidebar_select(listw))
            self._sidebar_lists.append(lst)
            layout.addWidget(lst)

        # NOTA: la selección inicial se hace desde _build_ui, después de que
        # también exista la parte detail (hero_title, etc.).

        layout.addStretch(1)

        scroll.setWidget(scroll_content)
        outer.addWidget(scroll, stretch=1)

        # Storage bar pinneado abajo (fuera del scroll — siempre visible)
        self.storage_bar = StorageBar()
        outer.addWidget(self.storage_bar)

        return sidebar

    def _refresh_storage(self):
        """Compat helper: refresca la barra de disco. Se llama después de limpiezas."""
        if hasattr(self, "storage_bar"):
            self.storage_bar.refresh()

    def _build_detail(self) -> QWidget:
        detail = QWidget()
        v = QVBoxLayout(detail)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Header
        header = QWidget()
        hv = QVBoxLayout(header)
        hv.setContentsMargins(Spacing.XXL, Spacing.XXL, Spacing.XXL, Spacing.LG)
        hv.setSpacing(Spacing.SM)

        self.hero_title = QLabel("Smart Scan")
        self.hero_title.setProperty("role", "hero")
        self.hero_subtitle = QLabel(SECTIONS_BY_KEY["Smart Scan"]["desc"])
        self.hero_subtitle.setProperty("role", "secondary")
        self.hero_subtitle.setWordWrap(True)
        hv.addWidget(self.hero_title)
        hv.addWidget(self.hero_subtitle)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, Spacing.LG, 0, 0)
        action_row.setSpacing(Spacing.MD)

        self.action_button = QPushButton("Analizar todo")
        self.action_button.setProperty("role", "positive")
        self.action_button.clicked.connect(self._on_action_clicked)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)

        action_row.addWidget(self.action_button)
        action_row.addWidget(self.progress_bar, stretch=1)
        hv.addLayout(action_row)
        v.addWidget(header)

        # Onboarding banner (aparece la primera vez que visitás cada sección)
        banner_wrap = QWidget()
        bw = QVBoxLayout(banner_wrap)
        bw.setContentsMargins(Spacing.XXL, 0, Spacing.XXL, Spacing.MD)
        bw.setSpacing(0)
        self.onboarding_banner = OnboardingBanner()
        self.onboarding_banner.dismissed.connect(self._on_onboarding_dismissed)
        bw.addWidget(self.onboarding_banner)
        v.addWidget(banner_wrap)

        # Stack de páginas
        self.stack = QStackedWidget()
        self.page_dashboard = self._build_dashboard_page()
        self.page_categories = self._build_categories_page()
        self.page_duplicates = self._build_duplicates_page()
        self.page_uninstaller = self._build_uninstaller_page()
        self.page_large = self._build_large_page()
        self.page_startup = self._build_startup_page()
        self.page_updater = self._build_updater_page()
        self.page_memory = self._build_memory_page()
        self.page_stats = self._build_stats_page()
        self.page_permissions = self._build_permissions_page()
        self.page_performance = self._build_performance_page()
        self.perf_rows = []  # inicializar
        self.stack.addWidget(self.page_dashboard)     # 0
        self.stack.addWidget(self.page_categories)    # 1
        self.stack.addWidget(self.page_duplicates)    # 2
        self.stack.addWidget(self.page_uninstaller)   # 3
        self.stack.addWidget(self.page_large)         # 4
        self.stack.addWidget(self.page_startup)       # 5
        self.stack.addWidget(self.page_updater)       # 6
        self.stack.addWidget(self.page_memory)        # 7
        self.stack.addWidget(self.page_stats)         # 8
        self.stack.addWidget(self.page_permissions)   # 9
        self.stack.addWidget(self.page_performance)   # 10
        v.addWidget(self.stack, stretch=1)

        # Footer
        self.footer = QWidget()
        fh = QHBoxLayout(self.footer)
        fh.setContentsMargins(Spacing.XXL, Spacing.LG, Spacing.XXL, Spacing.LG)
        fh.setSpacing(Spacing.LG)
        self.total_label = QLabel("")
        self.total_label.setProperty("role", "h3")
        self.clean_button = QPushButton("Limpiar seleccionados")
        self.clean_button.setProperty("role", "destructive")
        self.clean_button.setEnabled(False)
        fh.addWidget(self.total_label)
        fh.addStretch(1)
        fh.addWidget(self.clean_button)
        v.addWidget(self.footer)

        # Aplicar defaults (dashboard visible, footer oculto)
        self._show_section("Smart Scan")

        return detail

    # ---- Páginas ----

    def _build_dashboard_page(self) -> QWidget:
        page = QScrollArea()
        page.setObjectName("detail-scroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)

        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(Spacing.XXL, 0, Spacing.XXL, Spacing.XL)
        v.setSpacing(Spacing.LG)

        grid = QGridLayout()
        grid.setSpacing(Spacing.LG)

        # Mostrar cards para todas las secciones EXCEPTO Smart Scan mismo
        cards = [s for s in SECTIONS if s["key"] != "Smart Scan"]
        cols = 2
        for i, s in enumerate(cards):
            card = DashboardCard(s)
            card.clicked.connect(self._select_section)
            self.dashboard_cards[s["key"]] = card
            grid.addWidget(card, i // cols, i % cols)

        v.addLayout(grid)
        v.addStretch(1)

        page.setWidget(wrap)
        return page

    def _build_categories_page(self) -> QWidget:
        page = QScrollArea()
        page.setObjectName("detail-scroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        self.rows_layout = QVBoxLayout(content)
        self.rows_layout.setContentsMargins(Spacing.XXL, 0, Spacing.XXL, Spacing.XL)
        self.rows_layout.setSpacing(Spacing.SM)
        for cat in self.categories:
            row = CategoryRow(cat)
            row.checked_changed.connect(self._update_footer)
            self.rows[cat["id"]] = row
            self.rows_layout.addWidget(row)
        self.rows_layout.addStretch(1)
        page.setWidget(content)
        return page

    def _build_duplicates_page(self) -> QWidget:
        page = QScrollArea()
        page.setObjectName("detail-scroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        self.dup_layout = QVBoxLayout(content)
        self.dup_layout.setContentsMargins(Spacing.XXL, 0, Spacing.XXL, Spacing.XL)
        self.dup_layout.setSpacing(Spacing.SM)
        self.dup_empty = EmptyState(
            icon_name="copy",
            title="Encontrá archivos duplicados",
            body="Escanea Descargas, Documentos, Escritorio, Imágenes y Videos "
                 "buscando archivos idénticos (mismo contenido, no solo mismo "
                 "nombre). Solo archivos de más de 1 MB para evitar ruido.",
            action_label="Buscar duplicados",
            action_callback=lambda: self.start_duplicates_scan(),
        )
        self.dup_layout.addWidget(self.dup_empty)
        self.dup_layout.addStretch(1)
        page.setWidget(content)
        return page

    def _build_uninstaller_page(self) -> QWidget:
        page = QScrollArea()
        page.setObjectName("detail-scroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        self.app_layout = QVBoxLayout(content)
        self.app_layout.setContentsMargins(Spacing.XXL, 0, Spacing.XXL, Spacing.XL)
        self.app_layout.setSpacing(Spacing.SM)

        # Search bar (visible cuando hay apps cargadas)
        self.app_search = QLineEdit()
        self.app_search.setObjectName("section-search")
        self.app_search.setPlaceholderText("Buscar app por nombre o bundle ID…")
        self.app_search.textChanged.connect(self._filter_apps)
        self.app_search.setVisible(False)
        self.app_layout.addWidget(self.app_search)

        self.app_empty = EmptyState(
            icon_name="app-window",
            title="Explorá tus apps instaladas",
            body="Encontrá cada app junto con el tamaño real que ocupa "
                 "(incluyendo rastros en ~/Library). Las que no abrís hace "
                 "6+ meses aparecen primero, marcadas para desinstalar.",
            action_label="Cargar apps instaladas",
            action_callback=lambda: self.start_uninstaller_scan(),
        )
        self.app_layout.addWidget(self.app_empty)
        self.app_layout.addStretch(1)
        page.setWidget(content)
        return page

    def _filter_apps(self, text: str):
        """Filtra las filas del desinstalador por texto de búsqueda."""
        t = text.strip().lower()
        for row in getattr(self, "app_rows", []):
            if not t:
                row.setVisible(True)
                continue
            name = row.app["name"].lower()
            bid = row.app["bundle_id"].lower()
            row.setVisible(t in name or t in bid)

    def _build_large_page(self) -> QWidget:
        page = QScrollArea()
        page.setObjectName("detail-scroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        self.large_layout = QVBoxLayout(content)
        self.large_layout.setContentsMargins(Spacing.XXL, 0, Spacing.XXL, Spacing.XL)
        self.large_layout.setSpacing(Spacing.SM)
        self.large_empty = EmptyState(
            icon_name="hard-drive",
            title="Archivos grandes olvidados",
            body="Encontrá archivos de más de 100 MB que no abrís hace 6+ meses. "
                 "Escanea Descargas, Documentos, Escritorio, Imágenes y Videos. "
                 "Revisá cada uno antes de borrar — puede haber cosas importantes.",
            action_label="Buscar archivos grandes",
            action_callback=lambda: self.start_large_scan(),
        )
        self.large_layout.addWidget(self.large_empty)
        self.large_layout.addStretch(1)
        page.setWidget(content)
        return page

    def _build_startup_page(self) -> QWidget:
        page = QScrollArea()
        page.setObjectName("detail-scroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        self.startup_layout = QVBoxLayout(content)
        self.startup_layout.setContentsMargins(Spacing.XXL, 0, Spacing.XXL, Spacing.XL)
        self.startup_layout.setSpacing(Spacing.SM)
        self.startup_empty = EmptyState(
            icon_name="power",
            title="Gestioná los agentes de inicio",
            body="Mostrá los LaunchAgents del usuario que arrancan con tu Mac. "
                 "Los que están marcados con badge naranja son bloatware conocido "
                 "que podés desactivar sin riesgo.",
            action_label="Cargar agentes",
            action_callback=lambda: self._load_startup_items(),
        )
        self.startup_layout.addWidget(self.startup_empty)
        self.startup_layout.addStretch(1)
        page.setWidget(content)
        return page

    def _build_updater_page(self) -> QWidget:
        page = QScrollArea()
        page.setObjectName("detail-scroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        self.updater_layout = QVBoxLayout(content)
        self.updater_layout.setContentsMargins(Spacing.XXL, 0, Spacing.XXL, Spacing.XL)
        self.updater_layout.setSpacing(Spacing.SM)
        self.updater_empty = EmptyState(
            icon_name="download",
            title="Actualizá paquetes de Homebrew",
            body="Consulta cuáles de tus formulae y casks tienen updates "
                 "disponibles. Podés actualizar todos de una o seleccionar "
                 "específicos. Requiere Homebrew instalado.",
            action_label="Buscar actualizaciones",
            action_callback=lambda: self.start_scan_updates(),
        )
        self.updater_layout.addWidget(self.updater_empty)
        self.updater_layout.addStretch(1)
        page.setWidget(content)
        return page

    def _build_performance_page(self) -> QWidget:
        page = QScrollArea()
        page.setObjectName("detail-scroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        self.perf_layout = QVBoxLayout(content)
        self.perf_layout.setContentsMargins(Spacing.XXL, 0, Spacing.XXL, Spacing.XL)
        self.perf_layout.setSpacing(Spacing.SM)

        # Card de estado de RAM del sistema (se refresca al escanear)
        self.perf_memory_card = QFrame()
        self.perf_memory_card.setObjectName("category-row")
        pmv = QVBoxLayout(self.perf_memory_card)
        pmv.setContentsMargins(Spacing.XL, Spacing.LG, Spacing.XL, Spacing.LG)
        self.perf_memory_title = QLabel("Estado de la memoria RAM")
        self.perf_memory_title.setObjectName("row-name")
        self.perf_memory_text = QLabel("Presioná 'Buscar procesos' para ver el estado actual.")
        self.perf_memory_text.setObjectName("row-desc")
        self.perf_memory_text.setWordWrap(True)
        pmv.addWidget(self.perf_memory_title)
        pmv.addWidget(self.perf_memory_text)
        self.perf_layout.addWidget(self.perf_memory_card)

        self.perf_empty = EmptyState(
            icon_name="cpu",
            title="Recuperá memoria virtual",
            body="Escaneo las apps que más RAM están consumiendo. Podés "
                 "SUSPENDERLAS (sin cerrarlas, sin perder datos) para liberar "
                 "memoria virtual al toque. Después las reanudás cuando quieras.",
            action_label="Buscar procesos",
            action_callback=lambda: self.start_perf_scan(),
        )
        self.perf_layout.addWidget(self.perf_empty)
        self.perf_layout.addStretch(1)
        page.setWidget(content)
        return page

    def _build_permissions_page(self) -> QWidget:
        page = QScrollArea()
        page.setObjectName("detail-scroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(Spacing.XXL, 0, Spacing.XXL, Spacing.XL)
        v.setSpacing(Spacing.LG)

        # Card principal: acceso completo al disco
        card = QFrame()
        card.setObjectName("category-row")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(Spacing.XL, Spacing.LG, Spacing.XL, Spacing.LG)
        cv.setSpacing(Spacing.MD)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon_pixmap("hard-drive", size=32, color=Colors.SUCCESS))
        icon_lbl.setFixedSize(48, 48)
        cv.addWidget(icon_lbl)

        title = QLabel("Acceso completo al disco (recomendado)")
        title.setProperty("role", "h2")
        cv.addWidget(title)

        body = QLabel(
            "macOS te pregunta cada vez que una app quiere entrar a Downloads, "
            "Documents, Desktop, Movies, etc. Es tedioso — sobre todo al escanear "
            "duplicados y archivos grandes que recorren muchas carpetas.\n\n"
            "Si le das \"Acceso completo al disco\" a CleanMyCompu en Preferencias "
            "del Sistema, macOS deja de preguntar de una vez.\n\n"
            "Cómo hacerlo (30 segundos, una única vez):\n"
            "  1. Tocá el botón verde acá abajo — te abre el panel exacto.\n"
            "  2. En la lista de la derecha, dale al botón + de abajo.\n"
            "  3. Buscá CleanMyCompu en /Applications y agregala.\n"
            "  4. Reabrí CleanMyCompu."
        )
        body.setObjectName("row-desc")
        body.setWordWrap(True)
        cv.addWidget(body)

        btn_row = QHBoxLayout()
        btn = QPushButton("Abrir Preferencias del Sistema")
        btn.setProperty("role", "positive")
        btn.clicked.connect(permissions.open_full_disk_access)
        btn_row.addWidget(btn)
        btn_row.addStretch(1)
        cv.addLayout(btn_row)

        v.addWidget(card)

        # Card secundaria: permisos por carpeta
        card2 = QFrame()
        card2.setObjectName("category-row")
        c2v = QVBoxLayout(card2)
        c2v.setContentsMargins(Spacing.XL, Spacing.LG, Spacing.XL, Spacing.LG)
        c2v.setSpacing(Spacing.MD)

        title2 = QLabel("Permisos por carpeta (alternativa)")
        title2.setProperty("role", "h3")
        c2v.addWidget(title2)

        body2 = QLabel(
            "Si preferís no dar acceso completo al disco, podés revisar y ajustar "
            "los permisos que le diste (o no) por carpeta individual. Ojo: cada "
            "carpeta que rechaces, la app no va a poder escanearla."
        )
        body2.setObjectName("row-desc")
        body2.setWordWrap(True)
        c2v.addWidget(body2)

        btn2_row = QHBoxLayout()
        btn2 = QPushButton("Abrir permisos por carpeta")
        btn2.setProperty("role", "secondary")
        btn2.clicked.connect(permissions.open_files_and_folders)
        btn2_row.addWidget(btn2)
        btn2_row.addStretch(1)
        c2v.addLayout(btn2_row)

        v.addWidget(card2)
        v.addStretch(1)

        page.setWidget(content)
        return page

    def _build_stats_page(self) -> QWidget:
        page = QScrollArea()
        page.setObjectName("detail-scroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(Spacing.XXL, 0, Spacing.XXL, Spacing.XL)
        v.setSpacing(Spacing.LG)

        # 2 tarjetas: todo el tiempo + últimos 30 días
        cards_row = QHBoxLayout()
        cards_row.setSpacing(Spacing.LG)

        self.stat_total_card = self._build_stat_card(
            "DESDE EL INICIO", "0 B", "0 operaciones")
        cards_row.addWidget(self.stat_total_card)

        self.stat_recent_card = self._build_stat_card(
            "ÚLTIMOS 30 DÍAS", "0 B", "0 operaciones")
        cards_row.addWidget(self.stat_recent_card)
        v.addLayout(cards_row)

        # Desglose por categoría
        breakdown_title = QLabel("Desglose por categoría")
        breakdown_title.setProperty("role", "h3")
        v.addWidget(breakdown_title)
        self.stats_breakdown_layout = QVBoxLayout()
        self.stats_breakdown_layout.setSpacing(Spacing.SM)
        v.addLayout(self.stats_breakdown_layout)

        # Últimas operaciones
        latest_title = QLabel("Últimas operaciones")
        latest_title.setProperty("role", "h3")
        v.addWidget(latest_title)
        self.stats_latest_layout = QVBoxLayout()
        self.stats_latest_layout.setSpacing(Spacing.XS)
        v.addLayout(self.stats_latest_layout)

        v.addStretch(1)

        # Botón resetear (secondary, bottom aligned)
        reset_row = QHBoxLayout()
        reset_row.addStretch(1)
        reset_btn = QPushButton("Resetear historial")
        reset_btn.setProperty("role", "secondary")
        reset_btn.clicked.connect(self._reset_stats)
        reset_row.addWidget(reset_btn)
        v.addLayout(reset_row)

        page.setWidget(content)
        return page

    def _build_stat_card(self, header: str, big: str, sub: str) -> QFrame:
        card = QFrame()
        card.setObjectName("category-row")
        card.setMinimumHeight(120)
        v = QVBoxLayout(card)
        v.setContentsMargins(Spacing.XL, Spacing.LG, Spacing.XL, Spacing.LG)
        v.setSpacing(Spacing.XS)
        h = QLabel(header)
        h.setProperty("role", "caption")
        big_lbl = QLabel(big)
        big_lbl.setProperty("role", "hero")
        sub_lbl = QLabel(sub)
        sub_lbl.setProperty("role", "secondary")
        v.addWidget(h)
        v.addWidget(big_lbl)
        v.addWidget(sub_lbl)
        # Guardamos referencias para actualizar
        card._big = big_lbl
        card._sub = sub_lbl
        return card

    def _refresh_stats(self):
        s = stats.summary()
        # Cards
        self.stat_total_card._big.setText(human_bytes(s["total_bytes"]))
        self.stat_total_card._sub.setText(f"{s['total_ops']} operaciones")
        self.stat_recent_card._big.setText(human_bytes(s["recent_bytes"]))
        self.stat_recent_card._sub.setText(f"{s['recent_ops']} operaciones")

        # Breakdown por categoría — limpiar y repopular
        while self.stats_breakdown_layout.count():
            it = self.stats_breakdown_layout.takeAt(0)
            if it.widget():
                it.widget().setParent(None)
        max_bytes = max((b for _, b in s["by_source"]), default=1)
        for src, bytes_ in s["by_source"][:15]:
            row = QFrame()
            row.setObjectName("category-row")
            h = QHBoxLayout(row)
            h.setContentsMargins(Spacing.LG, Spacing.SM, Spacing.LG, Spacing.SM)
            name = QLabel(src)
            name.setObjectName("row-name")
            name.setMinimumWidth(180)
            # Mini barra proporcional
            bar_wrap = QWidget()
            bar_wrap.setFixedHeight(6)
            bl = QHBoxLayout(bar_wrap)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(0)
            fill = QFrame()
            fill.setStyleSheet(
                f"background: {Colors.SUCCESS_DARK if is_dark_mode() else Colors.SUCCESS};"
                " border-radius: 3px;")
            spacer = QWidget()
            bl.addWidget(fill, stretch=max(1, int(bytes_ * 100 / max_bytes)))
            bl.addWidget(spacer, stretch=max(1, int((max_bytes - bytes_) * 100 / max_bytes)))
            size = QLabel(human_bytes(bytes_))
            size.setObjectName("row-size")
            size.setMinimumWidth(80)
            size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            h.addWidget(name)
            h.addWidget(bar_wrap, stretch=1)
            h.addWidget(size)
            self.stats_breakdown_layout.addWidget(row)
        if not s["by_source"]:
            empty = QLabel("Todavía no limpiaste nada. Corré 'Analizar todo' desde Smart Scan.")
            empty.setObjectName("row-desc")
            empty.setWordWrap(True)
            self.stats_breakdown_layout.addWidget(empty)

        # Últimas operaciones
        while self.stats_latest_layout.count():
            it = self.stats_latest_layout.takeAt(0)
            if it.widget():
                it.widget().setParent(None)
        for r in s["latest"]:
            row = QFrame()
            row.setObjectName("category-row")
            h = QHBoxLayout(row)
            h.setContentsMargins(Spacing.LG, Spacing.SM, Spacing.LG, Spacing.SM)
            date = QLabel(r["date"].replace("T", " "))
            date.setObjectName("row-desc")
            date.setMinimumWidth(160)
            src = QLabel(r.get("source", "?"))
            src.setObjectName("row-name")
            size = QLabel(human_bytes(r.get("bytes", 0)))
            size.setObjectName("row-size")
            size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            h.addWidget(date)
            h.addWidget(src, stretch=1)
            h.addWidget(size)
            self.stats_latest_layout.addWidget(row)
        if not s["latest"]:
            empty = QLabel("Sin operaciones registradas todavía.")
            empty.setObjectName("row-desc")
            self.stats_latest_layout.addWidget(empty)

    def _reset_stats(self):
        dlg = ConfirmDialog(
            title="Borrar historial",
            body=("¿Seguro querés resetear todo el historial de limpiezas? "
                  "Esto no borra archivos, solo el registro que llevamos "
                  "en ~/.cleanmycompu/stats.json."),
            icon_name="trash",
            icon_color=Colors.WARNING,
            ok_label="Sí, borrar historial",
            cancel_label="Cancelar",
            ok_role="destructive",
            parent=self,
        )
        if dlg.exec() == QDialog.Accepted:
            stats.reset()
            self._refresh_stats()

    def _build_memory_page(self) -> QWidget:
        page = QScrollArea()
        page.setObjectName("detail-scroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(Spacing.XXL, 0, Spacing.XXL, Spacing.XL)
        v.setSpacing(Spacing.LG)
        self.memory_bar = MemoryStatBar()
        v.addWidget(self.memory_bar)
        note = QLabel(
            "El botón verde arriba (\"Liberar RAM inactiva\") ejecuta el comando "
            "'purge' del sistema con permisos de admin. macOS te va a pedir la "
            "contraseña. Es 100% seguro — solo libera páginas que estaban en "
            "cache y no las estaba usando ninguna app activa."
        )
        note.setObjectName("row-desc")
        note.setWordWrap(True)
        v.addWidget(note)
        v.addStretch(1)
        page.setWidget(content)
        return page

    # ---- Tema ----

    def _apply_theme(self):
        dark = is_dark_mode()
        QApplication.instance().setStyleSheet(build_stylesheet(dark=dark))
        for row in self.rows.values():
            row._refresh_icon()

    # ---- Navegación / sidebar ----

    def _on_sidebar_select(self, active_list: QListWidget):
        it = active_list.currentItem()
        if it is None:
            return
        # Deseleccionar el resto de listas
        for lst in self._sidebar_lists:
            if lst is not active_list:
                lst.blockSignals(True)
                lst.clearSelection()
                lst.setCurrentRow(-1)
                lst.blockSignals(False)
        section = it.data(Qt.UserRole)
        self._show_section(section)

    def _select_section(self, section_key: str):
        """Selecciona una sección desde código (ej. click en card del dashboard)."""
        for lst in self._sidebar_lists:
            for i in range(lst.count()):
                if lst.item(i).data(Qt.UserRole) == section_key:
                    lst.setCurrentRow(i)
                    return

    def _show_section(self, section: str):
        self.current_section = section
        info = SECTIONS_BY_KEY.get(section, {"desc": ""})
        self.hero_title.setText(section)
        self.hero_subtitle.setText(info.get("desc", ""))
        self._refresh_action_button_visibility(section)

        # Onboarding: mostrar tip la primera vez que se abre la sección
        if section in ONBOARDING and section not in self.visited_sections:
            title, body = ONBOARDING[section]
            self.onboarding_banner.show_tip(title, body)
            self._pending_visit = section  # se marca visitado al dismissar
        else:
            self.onboarding_banner.hide()
            self._pending_visit = None
        # Reconectar el botón de acción sin duplicar
        try:
            self.clean_button.clicked.disconnect()
        except Exception:
            pass

        if section == "Smart Scan":
            self.stack.setCurrentIndex(0)
            self.action_button.setText("Analizar todo")
            self.footer.setVisible(False)
        elif section in ("Sistema", "Navegadores", "Restos de programas", "Desarrollo"):
            self.stack.setCurrentIndex(1)
            self.action_button.setText("Analizar mi Compu")
            self._apply_category_filter(section)
            self.footer.setVisible(True)
            self.clean_button.setText("Limpiar seleccionados")
            self.clean_button.clicked.connect(self.start_clean)
        elif section == "Duplicados":
            self.stack.setCurrentIndex(2)
            self.action_button.setText("Buscar duplicados")
            self.footer.setVisible(True)
            self.clean_button.setText("Borrar duplicados seleccionados")
            self.clean_button.clicked.connect(self.start_dup_clean)
        elif section == "Desinstalador":
            self.stack.setCurrentIndex(3)
            self.action_button.setText("Cargar apps instaladas")
            self.footer.setVisible(False)
        elif section == "Archivos grandes":
            self.stack.setCurrentIndex(4)
            self.action_button.setText("Buscar archivos grandes")
            self.footer.setVisible(True)
            self.clean_button.setText("Borrar seleccionados")
            self.clean_button.clicked.connect(self.start_large_clean)
        elif section == "Elementos de inicio":
            self.stack.setCurrentIndex(5)
            self.action_button.setText("Recargar lista")
            self.footer.setVisible(False)
            # auto-cargar la primera vez
            if not self.startup_rows:
                self._load_startup_items()
        elif section == "Actualizador":
            self.stack.setCurrentIndex(6)
            self.action_button.setText("Buscar actualizaciones")
            self.footer.setVisible(True)
            self.clean_button.setText("Actualizar seleccionados")
            self.clean_button.setEnabled(False)
            self.clean_button.clicked.connect(self.start_upgrade_selected)
        elif section == "Memoria":
            self.stack.setCurrentIndex(7)
            self.action_button.setText("Liberar RAM inactiva")
            self.footer.setVisible(False)
            self._refresh_memory_stats()
        elif section == "Estadísticas":
            self.stack.setCurrentIndex(8)
            self.action_button.setVisible(False)
            self.footer.setVisible(False)
            self._refresh_stats()
        elif section == "Permisos":
            self.stack.setCurrentIndex(9)
            self.action_button.setVisible(False)
            self.footer.setVisible(False)
        elif section == "Rendimiento":
            self.stack.setCurrentIndex(10)
            self.action_button.setText("Buscar procesos")
            self.footer.setVisible(False)
        self._update_footer()

    def _apply_category_filter(self, group: str):
        for cat in self.categories:
            visible = cat.get("group") == group
            self.rows[cat["id"]].setVisible(visible)

    # ---- Acción principal (contexto por sección) ----

    def _refresh_action_button_visibility(self, section: str = None):
        """
        Para secciones que muestran empty state con CTA central (Duplicados,
        Desinstalador, Archivos grandes, Actualizador), ocultar el botón de
        arriba mientras no haya datos cargados — evita botón duplicado. Cuando
        ya hay resultados en pantalla, mostrar el botón de arriba para poder
        re-escanear.
        """
        section = section or self.current_section
        # Estadísticas y Permisos nunca tienen botón de acción arriba
        if section in ("Estadísticas", "Permisos"):
            self.action_button.setVisible(False)
            return
        empty_when_no_data = {
            "Duplicados": lambda: not self.dup_rows,
            "Desinstalador": lambda: not self.app_rows,
            "Archivos grandes": lambda: not self.large_rows,
            "Actualizador": lambda: not getattr(self, "updater_rows", []),
            "Rendimiento": lambda: not getattr(self, "perf_rows", []),
        }
        check = empty_when_no_data.get(section)
        should_hide = check() if check else False
        self.action_button.setVisible(not should_hide)

    def _on_action_clicked(self):
        s = self.current_section
        if s == "Smart Scan" or s in ("Sistema", "Navegadores", "Restos de programas", "Desarrollo"):
            self.start_scan()
        elif s == "Duplicados":
            self.start_duplicates_scan()
        elif s == "Desinstalador":
            self.start_uninstaller_scan()
        elif s == "Archivos grandes":
            self.start_large_scan()
        elif s == "Elementos de inicio":
            self._load_startup_items()
        elif s == "Actualizador":
            self.start_scan_updates()
        elif s == "Memoria":
            self.free_memory()
        elif s == "Rendimiento":
            self.start_perf_scan()

    # ---- Escaneo de categorías ----

    def start_scan(self):
        self.action_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.scan_results.clear()
        for row in self.rows.values():
            row.reset()
        self.statusBar().showMessage("Analizando…")

        # Modal con overlay: spinner circular verde
        self.overlay.show_over()
        self.progress_dialog = ProgressDialog(
            "Analizando tu compu…", parent=self,
            spinner_color=Colors.SUCCESS_DARK if is_dark_mode() else Colors.SUCCESS,
        )
        self._scan_count = 0
        self._scan_total = len(self.categories)
        self.progress_dialog.show()

        self.thread = QThread()
        self.worker = ScanWorker(self.categories)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.detail.connect(
            lambda m: self.progress_dialog.set_detail(m) if self.progress_dialog else None)
        self.worker.category_scanned.connect(self._on_scanned)
        self.worker.finished.connect(self._on_scan_done)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_scanned(self, result: dict):
        self.scan_results[result["id"]] = result
        row = self.rows.get(result["id"])
        if row:
            row.set_result(result)
        self._scan_count += 1
        if self.progress_dialog:
            self.progress_dialog.set_title(
                f"Analizando tu compu…  ({self._scan_count}/{self._scan_total})")
        self._update_dashboard_cards()
        self._update_footer()

    def _on_scan_done(self):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.overlay.hide()
        self.action_button.setEnabled(True)
        total = sum(r["bytes"] for r in self.scan_results.values())
        self.statusBar().showMessage(
            f"Análisis completo. Se pueden liberar hasta {human_bytes(total)}.")
        self._update_dashboard_cards()
        self._update_footer()
        if not self.isActiveWindow():
            notify("Análisis completo",
                   f"Podés liberar hasta {human_bytes(total)}.",
                   subtitle="CleanMyCompu")

        # Modal celebratorio con total encontrado + breakdown por grupo
        if total > 0:
            by_group = {}
            for cat in self.categories:
                r = self.scan_results.get(cat["id"])
                if r and r["bytes"] > 0:
                    g = cat.get("group", "Otros")
                    by_group[g] = by_group.get(g, 0) + r["bytes"]
            breakdown = "\n".join(
                f"   • {g}: {human_bytes(b)}"
                for g, b in sorted(by_group.items(), key=lambda x: -x[1])
            )
            InfoDialog(
                title=f"¡Encontramos {human_bytes(total)} para liberar!",
                body=(f"Análisis completo. Se puede recuperar espacio en:\n\n"
                      f"{breakdown}\n\n"
                      "Entrá a cada categoría para decidir qué limpiar."),
                icon_name="sparkles",
                icon_color=Colors.SUCCESS,
                parent=self,
            ).exec()
        else:
            InfoDialog(
                title="¡Todo limpio!",
                body="No encontramos nada para liberar. Tu compu está en orden.",
                icon_name="check-circle",
                icon_color=Colors.SUCCESS,
                parent=self,
            ).exec()

    def _celebrate(self):
        """Dispara confetti sobre la ventana. Se autodestruye al terminar."""
        try:
            c = Confetti(self.centralWidget())
            c.raise_()
            c.show()
        except Exception:
            pass  # celebrar nunca debe romper el flujo

    def _update_dashboard_cards(self):
        # Sumar por grupo
        by_group = {}
        for cat in self.categories:
            g = cat.get("group")
            r = self.scan_results.get(cat["id"])
            if r:
                by_group[g] = by_group.get(g, 0) + r["bytes"]
        for section_key, card in self.dashboard_cards.items():
            if section_key in by_group:
                total = by_group[section_key]
                if total > 0:
                    card.set_status(f"{human_bytes(total)} para liberar", highlight=True)
                else:
                    card.set_status("Todo limpio")
            # Tools cards se actualizan por sus propios flujos

    # ---- Footer ----

    def _visible_selected_rows(self) -> List[CategoryRow]:
        return [r for r in self.rows.values() if r.isVisible() and r.is_selected()]

    def _update_footer(self, *args):
        s = self.current_section
        if s in ("Sistema", "Navegadores", "Restos de programas", "Desarrollo"):
            rows = self._visible_selected_rows()
            total = sum(r.scan_result["bytes"] for r in rows)
            self.total_label.setText(f"Total seleccionado: {human_bytes(total)}")
            self.clean_button.setEnabled(len(rows) > 0 and total > 0)
        elif s == "Duplicados":
            total = sum(dr.bytes_to_free() for dr in self.dup_rows)
            self.total_label.setText(f"Total a liberar: {human_bytes(total)}")
            self.clean_button.setEnabled(total > 0)
        elif s == "Archivos grandes":
            selected = [lr for lr in self.large_rows if lr.is_selected()]
            total = sum(lr.item["size"] for lr in selected)
            self.total_label.setText(f"Total seleccionado: {human_bytes(total)}")
            self.clean_button.setEnabled(len(selected) > 0)
        elif s == "Actualizador":
            selected = [r for r in getattr(self, "updater_rows", [])
                        if r.is_selected()]
            n = len(selected)
            self.total_label.setText(
                f"{n} paquete(s) seleccionado(s)" if n
                else "Marcá los paquetes que querés actualizar")
            self.clean_button.setEnabled(n > 0)
        else:
            self.total_label.setText("")
            self._refresh_action_button_visibility(s)
            return
        # Refrescar visibilidad del botón superior (ocultar si hay CTA en empty state)
        self._refresh_action_button_visibility(s)

        # Prompt guía cuando no hay nada seleccionado (en vez del "0 B" muerto)
        if s in ("Sistema", "Navegadores", "Restos de programas", "Desarrollo"):
            rows = self._visible_selected_rows()
            if not rows:
                self.total_label.setText("Marcá qué querés limpiar")
        elif s == "Duplicados" and not any(dr.bytes_to_free() > 0 for dr in self.dup_rows):
            if self.dup_rows:
                self.total_label.setText("Marcá copias para borrar")
        elif s == "Archivos grandes":
            selected_l = [lr for lr in self.large_rows if lr.is_selected()]
            if not selected_l and self.large_rows:
                self.total_label.setText("Marcá archivos para borrar")

    # ---- Limpieza categorías ----

    def start_clean(self):
        rows = self._visible_selected_rows()
        selected = [self._find_cat(r.category_id) for r in rows]
        selected = [c for c in selected if c is not None]
        if not selected:
            return
        total_bytes = sum(self.scan_results[c["id"]]["bytes"] for c in selected)
        items = [{"name": c["name"], "icon": c.get("icon", "ghost"),
                  "bytes": self.scan_results[c["id"]]["bytes"]}
                 for c in selected]
        dialog = ConfirmCleanDialog(items, total_bytes, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return

        self.overlay.show_over()
        self.progress_dialog = ProgressDialog("Limpiando…", parent=self)
        self.progress_dialog.show()
        self.action_button.setEnabled(False)
        self.clean_button.setEnabled(False)

        self.thread = QThread()
        self.worker = CleanWorker(selected)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.category_started.connect(
            lambda name: self.progress_dialog.set_title(f"Limpiando {name}…"))
        self.worker.progress.connect(
            lambda m: self.progress_dialog.set_detail(m) if self.progress_dialog else None)
        self.worker.category_done.connect(self._on_category_cleaned)
        self.worker.finished.connect(self._on_clean_done)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_category_cleaned(self, cat_id: str, freed):
        row = self.rows.get(cat_id)
        if row:
            row.mark_cleaned()
        cat = self._find_cat(cat_id)
        stats.record(cat["name"] if cat else cat_id, freed)

    def _on_clean_done(self, freed_bytes):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.overlay.hide()
        self.action_button.setEnabled(True)
        self.storage_bar.refresh()
        for cat_id in list(self.scan_results.keys()):
            if self.rows.get(cat_id) and self.rows[cat_id].scan_result:
                self.scan_results[cat_id] = self.rows[cat_id].scan_result
        self._update_dashboard_cards()
        self._update_footer()
        self.statusBar().showMessage(f"¡Listo! Liberaste {human_bytes(freed_bytes)}.")
        if freed_bytes > 0:
            self._celebrate()
        if not self.isActiveWindow():
            notify(f"Liberaste {human_bytes(freed_bytes)}",
                   "La limpieza terminó correctamente.",
                   subtitle="CleanMyCompu", sound=True)
        InfoDialog(
            title=f"Liberaste {human_bytes(freed_bytes)}",
            body="Los archivos borrados eran regenerables o restos, así que las apps "
                 "seguirán funcionando normalmente.",
            icon_name="check-circle", icon_color=Colors.SUCCESS, parent=self,
        ).exec()

    # ---- Duplicados ----

    def start_duplicates_scan(self):
        self.action_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        for dr in self.dup_rows:
            dr.setParent(None)
        self.dup_rows = []
        self.dup_empty.setVisible(False)

        self.overlay.show_over()
        self.progress_dialog = ProgressDialog("Buscando duplicados…", parent=self)
        self.progress_dialog.show()

        self.thread = QThread()
        self.worker = DuplicatesWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(
            lambda m: self.progress_dialog.set_detail(m) if self.progress_dialog else None)
        self.worker.finished.connect(self._on_dup_scan_done)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_dup_scan_done(self, groups):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.overlay.hide()
        self.action_button.setEnabled(True)
        if not groups:
            self.dup_empty.setText("No se encontraron archivos duplicados. ✓")
            self.dup_empty.setVisible(True)
            self.clean_button.setEnabled(False)
            if "Duplicados" in self.dashboard_cards:
                self.dashboard_cards["Duplicados"].set_status("Sin duplicados")
            return
        insert_at = self.dup_layout.count() - 1
        for group in groups[:200]:
            row = DuplicateGroupRow(group)
            row.changed.connect(self._update_footer)
            self.dup_layout.insertWidget(insert_at, row)
            self.dup_rows.append(row)
            insert_at += 1
        total = sum(dr.bytes_to_free() for dr in self.dup_rows)
        self.statusBar().showMessage(
            f"{len(groups)} grupos de duplicados. Podés recuperar hasta {human_bytes(total)}.")
        if "Duplicados" in self.dashboard_cards:
            self.dashboard_cards["Duplicados"].set_status(
                f"{len(groups)} grupos · {human_bytes(total)}", highlight=True)
        self._update_footer()
        if not self.isActiveWindow():
            notify("Duplicados encontrados",
                   f"{len(groups)} grupos · podés recuperar hasta {human_bytes(total)}.",
                   subtitle="CleanMyCompu")

    def start_dup_clean(self):
        to_delete = []
        for dr in self.dup_rows:
            to_delete.extend(dr.selected_paths())
        if not to_delete:
            return
        total = sum(dr.bytes_to_free() for dr in self.dup_rows)
        items = [{"name": f"{len(to_delete)} archivos duplicados",
                  "icon": "copy", "bytes": total}]
        if ConfirmCleanDialog(items, total, parent=self).exec() != QDialog.Accepted:
            return
        self.overlay.show_over()
        self.progress_dialog = ProgressDialog("Borrando duplicados…", parent=self)
        self.progress_dialog.show()
        freed = 0
        for p in to_delete:
            try:
                size = p.stat().st_size
                p.unlink()
                freed += size
                if self.progress_dialog:
                    self.progress_dialog.set_detail(str(p))
                QApplication.processEvents()
            except OSError:
                pass
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.overlay.hide()
        self.storage_bar.refresh()
        for dr in list(self.dup_rows):
            dr.setParent(None)
        self.dup_rows = []
        self.dup_empty.setText("Duplicados eliminados. Podés volver a buscar.")
        self.dup_empty.setVisible(True)
        self._update_footer()
        stats.record("Duplicados", freed, items=len(to_delete))
        if freed > 0:
            self._celebrate()
        if not self.isActiveWindow():
            notify(f"Liberaste {human_bytes(freed)}",
                   f"Se borraron {len(to_delete)} archivos duplicados.",
                   subtitle="CleanMyCompu", sound=True)
        InfoDialog(
            title=f"Liberaste {human_bytes(freed)}",
            body=f"Se borraron {len(to_delete)} archivos duplicados.",
            icon_name="check-circle", icon_color=Colors.SUCCESS, parent=self,
        ).exec()

    # ---- Desinstalador ----

    def start_uninstaller_scan(self):
        self.action_button.setEnabled(False)
        for r in self.app_rows:
            r.setParent(None)
        self.app_rows = []
        self.app_empty.setVisible(False)
        self.app_search.setVisible(False)
        self.app_search.clear()

        self.overlay.show_over()
        self.progress_dialog = ProgressDialog("Buscando apps instaladas…", parent=self)
        self.progress_dialog.show()

        self.thread = QThread()
        self.worker = UninstallerWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(
            lambda m: self.progress_dialog.set_detail(m) if self.progress_dialog else None)
        self.worker.finished.connect(self._on_uninstaller_done)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_uninstaller_done(self, apps):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.overlay.hide()
        self.action_button.setEnabled(True)
        if not apps:
            self.app_empty.setText("No se encontraron apps del usuario en /Applications.")
            self.app_empty.setVisible(True)
            self.app_search.setVisible(False)
            return
        # Con apps cargadas, mostrar el buscador
        self.app_search.setVisible(True)
        self.app_search.clear()
        # Filtrar recomendaciones ignoradas por el usuario
        for a in apps:
            if a["bundle_id"] in self.ignored_uninstall_recs:
                a["recommend"] = None
                a["reason"] = ""
        # Re-ordenar: recomendados primero
        apps.sort(key=lambda a: (0, -(a.get("months_unused") or 0), a["name"].lower())
                  if a.get("recommend") == "uninstall"
                  else (1, a["name"].lower()))

        insert_at = self.app_layout.count() - 1
        recommended = 0
        for app in apps:
            row = AppRow(app)
            row.uninstall_requested.connect(self._on_uninstall_requested)
            row.ignore_recommendation.connect(self._on_ignore_uninstall_rec)
            self.app_layout.insertWidget(insert_at, row)
            self.app_rows.append(row)
            insert_at += 1
            if app.get("recommend") == "uninstall":
                recommended += 1
        msg = f"{len(apps)} apps encontradas."
        if recommended:
            msg += f" {recommended} recomendadas para desinstalar."
        self.statusBar().showMessage(msg)
        if "Desinstalador" in self.dashboard_cards:
            self.dashboard_cards["Desinstalador"].set_status(
                f"{len(apps)} apps instaladas"
                + (f" · {recommended} sin usar" if recommended else ""))
        if not self.isActiveWindow():
            notify("Apps cargadas",
                   f"{len(apps)} apps encontradas"
                   + (f", {recommended} recomendadas para desinstalar." if recommended else "."),
                   subtitle="Desinstalador")

    def _on_ignore_uninstall_rec(self, bundle_id: str):
        self.ignored_uninstall_recs.add(bundle_id)
        self.settings.setValue("ignored_uninstall_recs",
                               list(self.ignored_uninstall_recs))
        # Recargar la vista para que la sugerencia desaparezca
        self.start_uninstaller_scan()

    def _on_uninstall_requested(self, app: dict):
        # 1) ¿Hay procesos corriendo relacionados? (main + helpers en background)
        procs = uninstaller.find_related_processes(app["name"], app["bundle_id"])
        if procs:
            dlg = RunningProcessesDialog(app["name"], procs, parent=self)
            if dlg.exec() != QDialog.Accepted:
                return
            # Cerrar con SIGTERM
            still = uninstaller.kill_processes([p["pid"] for p in procs], force=False)
            if still:
                # Algunos siguieron vivos → forzar SIGKILL
                uninstaller.kill_processes(still, force=True)

        # 2) Buscar todos los archivos relacionados y confirmar
        target = uninstaller.get_uninstall_targets(app)
        items = [
            {"name": f"{app['name']}.app (aplicación)",
             "icon": "app-window", "bytes": app["size"]}
        ]
        related_size = target["total_bytes"] - app["size"]
        if related_size > 0:
            items.append({
                "name": f"{len(target['related_paths'])} archivos relacionados en ~/Library",
                "icon": "trash", "bytes": related_size,
            })
        total = target["total_bytes"]
        dialog = ConfirmCleanDialog(items, total, parent=self)
        dialog.setWindowTitle(f"Desinstalar {app['name']}")
        if dialog.exec() != QDialog.Accepted:
            return

        # 3) Ejecutar la desinstalación en el thread principal (rápida)
        self.overlay.show_over()
        self.progress_dialog = ProgressDialog(f"Desinstalando {app['name']}…", parent=self)
        self.progress_dialog.show()
        QApplication.processEvents()

        result = uninstaller.uninstall_app(
            target,
            on_progress=lambda m: (
                self.progress_dialog.set_detail(m) if self.progress_dialog else None,
                QApplication.processEvents(),
            ),
        )

        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.overlay.hide()
        self.storage_bar.refresh()

        # 4) Quitar la fila de la UI (solo si el .app efectivamente se borró)
        app_still_there = Path(app["path"]).exists()
        if not app_still_there:
            for row in list(self.app_rows):
                if row.app["bundle_id"] == app["bundle_id"]:
                    row.setParent(None)
                    self.app_rows.remove(row)

        # 5) Mostrar resultado — éxito, o warning si algo quedó atrás
        freed = result["freed"]
        failed = result["failed"]
        if not failed:
            stats.record(f"Desinstalador: {app['name']}", freed)
            if freed > 0:
                self._celebrate()
            if not self.isActiveWindow():
                notify(f"{app['name']} desinstalada",
                       f"Liberaste {human_bytes(freed)}. App + rastros en Papelera.",
                       subtitle="CleanMyCompu", sound=True)
            InfoDialog(
                title=f"{app['name']} desinstalada",
                body=f"Liberaste {human_bytes(freed)}.\n"
                     f"La app y {len(target['related_paths'])} archivos relacionados "
                     "se movieron a la Papelera (podés recuperarlos si te arrepentís).",
                icon_name="check-circle", icon_color=Colors.SUCCESS, parent=self,
            ).exec()
        else:
            # Algo no se pudo borrar — chequear si es porque hay procesos
            still_procs = uninstaller.find_related_processes(
                app["name"], app["bundle_id"])
            if still_procs:
                # Ofrecer forzar cierre y reintentar solo los que fallaron
                dlg = RunningProcessesDialog(
                    app["name"], still_procs, parent=self, force_variant=True)
                if dlg.exec() == QDialog.Accepted:
                    uninstaller.kill_processes(
                        [p["pid"] for p in still_procs], force=True,
                        wait_seconds=1.0)
                    # Reintentar SOLO los paths que fallaron
                    retry_target = dict(target)
                    retry_target["all_paths"] = failed
                    self.overlay.show_over()
                    self.progress_dialog = ProgressDialog(
                        f"Reintentando {app['name']}…", parent=self)
                    self.progress_dialog.show()
                    QApplication.processEvents()
                    retry_result = uninstaller.uninstall_app(
                        retry_target,
                        on_progress=lambda m: (
                            self.progress_dialog.set_detail(m) if self.progress_dialog else None,
                            QApplication.processEvents(),
                        ),
                    )
                    if self.progress_dialog:
                        self.progress_dialog.close()
                        self.progress_dialog = None
                    self.overlay.hide()
                    freed += retry_result["freed"]
                    failed = retry_result["failed"]
                    # Actualizar UI
                    self.storage_bar.refresh()
                    if not Path(app["path"]).exists():
                        for row in list(self.app_rows):
                            if row.app["bundle_id"] == app["bundle_id"]:
                                row.setParent(None)
                                self.app_rows.remove(row)
                    if not failed:
                        InfoDialog(
                            title=f"{app['name']} desinstalada",
                            body=(f"Liberaste {human_bytes(freed)}. "
                                  "Los procesos fueron cerrados y todos los archivos "
                                  "se movieron a la Papelera."),
                            icon_name="check-circle", icon_color=Colors.SUCCESS,
                            parent=self,
                        ).exec()
                        return

            # Si llegamos acá: sigue habiendo failed.
            # Último recurso: ofrecer escalar a permisos de administrador.
            failed_names = "\n".join(f"   • {p.name}" for p in failed[:6])
            if len(failed) > 6:
                failed_names += f"\n   … y {len(failed) - 6} más"

            admin_dlg = ConfirmDialog(
                title="Requiere permisos de administrador",
                body=(f"{app['name']} fue instalada con un .pkg y sus archivos "
                      "pertenecen a root. Para borrarlos necesitamos autenticación.\n\n"
                      f"Archivos pendientes:\n{failed_names}\n\n"
                      "macOS te va a mostrar su diálogo nativo pidiendo contraseña. "
                      "Si tenés Touch ID configurado para admin, podés usar la huella "
                      "en vez de escribir la clave.\n\n"
                      "Esta acción es permanente (no van a la Papelera)."),
                icon_name="alert-triangle",
                icon_color=Colors.WARNING,
                ok_label="Autenticar y borrar",
                cancel_label="Cancelar",
                ok_role="destructive",
                parent=self,
            )
            if admin_dlg.exec() == QDialog.Accepted:
                self.overlay.show_over()
                self.progress_dialog = ProgressDialog(
                    "Esperando contraseña de admin…", parent=self)
                self.progress_dialog.set_detail(
                    "macOS va a mostrar su diálogo de autenticación.")
                self.progress_dialog.show()
                QApplication.processEvents()

                admin_result = uninstaller.uninstall_with_admin(failed)

                if self.progress_dialog:
                    self.progress_dialog.close()
                    self.progress_dialog = None
                self.overlay.hide()

                if admin_result["error"] == "cancelled":
                    # Usuario canceló la contraseña — mostrar parcial simple
                    InfoDialog(
                        title="Desinstalación parcial",
                        body=(f"Se liberaron {human_bytes(freed)}. Los archivos que "
                              "requerían admin quedaron sin borrar. Podés intentar "
                              "de nuevo o borrarlos manualmente desde Finder."),
                        icon_name="alert-triangle", icon_color=Colors.WARNING,
                        parent=self,
                    ).exec()
                    return

                freed += admin_result["freed"]
                failed = admin_result["failed"]

                # Actualizar UI si se pudo borrar la .app
                self.storage_bar.refresh()
                if not Path(app["path"]).exists():
                    for row in list(self.app_rows):
                        if row.app["bundle_id"] == app["bundle_id"]:
                            row.setParent(None)
                            self.app_rows.remove(row)

                if admin_result["success"]:
                    InfoDialog(
                        title=f"{app['name']} desinstalada",
                        body=(f"Liberaste {human_bytes(freed)}. Se borraron todos "
                              "los archivos usando permisos de administrador."),
                        icon_name="check-circle", icon_color=Colors.SUCCESS,
                        parent=self,
                    ).exec()
                    return
                # Si con admin todavía falló algo, caemos al parcial de abajo

            # Parcial final — pasó de todo y aún queda algo
            failed_names = "\n".join(f"   • {p}" for p in failed[:6])
            if len(failed) > 6:
                failed_names += f"\n   … y {len(failed) - 6} más"
            body_msg = (f"Se liberaron {human_bytes(freed)} pero {len(failed)} archivo(s) "
                        f"no pudieron borrarse:\n\n{failed_names}\n\n")
            # Si hubo error específico del último intento, mostrarlo
            try:
                if 'admin_result' in dir() and admin_result.get("error") and admin_result["error"] != "cancelled":
                    body_msg += f"Detalle del error:\n{admin_result['error'][:400]}\n\n"
            except Exception:
                pass
            body_msg += ("Última opción: borralos manualmente desde Finder (clic derecho → "
                         "Mover a la Papelera). Si Finder también falla, reiniciá la Mac.")
            InfoDialog(
                title="Desinstalación parcial",
                body=body_msg,
                icon_name="alert-triangle", icon_color=Colors.WARNING, parent=self,
            ).exec()

    # ---- Archivos grandes ----

    def start_large_scan(self):
        self.action_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        for r in self.large_rows:
            r.setParent(None)
        self.large_rows = []
        self.large_empty.setVisible(False)

        self.overlay.show_over()
        self.progress_dialog = ProgressDialog("Buscando archivos grandes…", parent=self)
        self.progress_dialog.show()

        self.thread = QThread()
        self.worker = LargeFilesWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(
            lambda m: self.progress_dialog.set_detail(m) if self.progress_dialog else None)
        self.worker.finished.connect(self._on_large_done)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_large_done(self, files):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.overlay.hide()
        self.action_button.setEnabled(True)
        if not files:
            self.large_empty.setText(
                "No se encontraron archivos grandes olvidados. ✓")
            self.large_empty.setVisible(True)
            if "Archivos grandes" in self.dashboard_cards:
                self.dashboard_cards["Archivos grandes"].set_status("Nada olvidado")
            return
        insert_at = self.large_layout.count() - 1
        total = 0
        for item in files[:500]:
            row = LargeFileRow(item)
            row.changed.connect(self._update_footer)
            self.large_layout.insertWidget(insert_at, row)
            self.large_rows.append(row)
            insert_at += 1
            total += item["size"]
        self.statusBar().showMessage(
            f"{len(files)} archivos grandes encontrados ({human_bytes(total)}).")
        if "Archivos grandes" in self.dashboard_cards:
            self.dashboard_cards["Archivos grandes"].set_status(
                f"{len(files)} archivos · {human_bytes(total)}", highlight=True)
        self._update_footer()
        if not self.isActiveWindow():
            notify("Archivos grandes",
                   f"{len(files)} archivos ocupando {human_bytes(total)}.",
                   subtitle="CleanMyCompu")

    def _refresh_large_empty_state(self):
        """Si no quedan filas, volver a mostrar el empty state."""
        if not self.large_rows:
            self.large_empty.set_body(
                "No hay más archivos grandes. Buscá de nuevo para ver el estado actual.")
            self.large_empty.setVisible(True)
            self._refresh_action_button_visibility()

    def start_large_clean(self):
        selected = [lr for lr in self.large_rows if lr.is_selected()]
        if not selected:
            return
        total = sum(lr.item["size"] for lr in selected)
        items = [{"name": f"{len(selected)} archivos grandes",
                  "icon": "hard-drive", "bytes": total}]
        if ConfirmCleanDialog(items, total, parent=self).exec() != QDialog.Accepted:
            return
        self.overlay.show_over()
        self.progress_dialog = ProgressDialog("Borrando archivos…", parent=self)
        self.progress_dialog.show()
        freed = 0
        for lr in selected:
            try:
                p = lr.item["path"]
                sz = p.stat().st_size
                p.unlink()
                freed += sz
                if self.progress_dialog:
                    self.progress_dialog.set_detail(str(p))
                lr.setParent(None)
                self.large_rows.remove(lr)
                QApplication.processEvents()
            except OSError:
                pass
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.overlay.hide()
        self.storage_bar.refresh()
        self._update_footer()
        self._refresh_large_empty_state()
        stats.record("Archivos grandes", freed, items=len(selected))
        if freed > 0:
            self._celebrate()
        if not self.isActiveWindow():
            notify(f"Liberaste {human_bytes(freed)}",
                   f"Se borraron {len(selected)} archivos grandes.",
                   subtitle="CleanMyCompu", sound=True)
        InfoDialog(
            title=f"Liberaste {human_bytes(freed)}",
            body=f"Se borraron {len(selected)} archivos grandes.",
            icon_name="check-circle", icon_color=Colors.SUCCESS, parent=self,
        ).exec()

    # ---- Elementos de inicio ----

    def _load_startup_items(self):
        for r in self.startup_rows:
            r.setParent(None)
        self.startup_rows = []
        items = startup_items.list_launch_agents()
        # Filtrar recomendaciones ignoradas
        for it in items:
            if it["label"] in self.ignored_startup_recs:
                it["recommend"] = None
                it["reason"] = ""
        # Re-ordenar tras filtrar
        items.sort(key=lambda it: (
            (0, it["name"].lower()) if it["recommend"] == "disable" and it["enabled"]
            else (1, it["name"].lower()) if it["recommend"] == "disable"
            else (2, it["name"].lower())
        ))
        if not items:
            self.startup_empty.setText(
                "No tenés agentes de inicio de usuario. ✓\n"
                "(~/Library/LaunchAgents está vacío o no existe)")
            self.startup_empty.setVisible(True)
            if "Elementos de inicio" in self.dashboard_cards:
                self.dashboard_cards["Elementos de inicio"].set_status("Sin agentes")
            return
        self.startup_empty.setVisible(False)
        insert_at = self.startup_layout.count() - 1
        active = 0
        recommended = 0
        for it in items:
            row = StartupItemRow(it)
            row.toggled.connect(self._on_startup_toggled)
            row.removed.connect(self._on_startup_removed)
            row.ignore_recommendation.connect(self._on_ignore_startup_rec)
            self.startup_layout.insertWidget(insert_at, row)
            self.startup_rows.append(row)
            insert_at += 1
            if it["enabled"]:
                active += 1
            if it.get("recommend") == "disable" and it["enabled"]:
                recommended += 1
        msg = f"{len(items)} agentes de inicio ({active} activos)."
        if recommended:
            msg += f" {recommended} recomendados desactivar."
        self.statusBar().showMessage(msg)
        if "Elementos de inicio" in self.dashboard_cards:
            self.dashboard_cards["Elementos de inicio"].set_status(
                f"{active} activos de {len(items)}"
                + (f" · {recommended} a revisar" if recommended else ""))

    def _on_ignore_startup_rec(self, label: str):
        self.ignored_startup_recs.add(label)
        self.settings.setValue("ignored_startup_recs",
                               list(self.ignored_startup_recs))
        self._load_startup_items()

    def _on_startup_toggled(self, item: dict, enable: bool):
        try:
            # En Mac pasamos el path, en Windows pasamos el item entero.
            # El wrapper dispatch en startup_items.py acepta ambos.
            arg = item if is_windows() else item.get("path")
            result = startup_items.toggle_launch_agent(arg, enable)
            if result is False:
                self.statusBar().showMessage(
                    "No se pudo cambiar el estado. Puede requerir permisos de admin.")
                return
            item["enabled"] = enable
            self._load_startup_items()
        except Exception as e:
            self.statusBar().showMessage(f"No se pudo cambiar: {e}")

    def _on_startup_removed(self, item: dict):
        arg = item if is_windows() else item.get("path")
        if startup_items.remove_launch_agent(arg):
            self._load_startup_items()
        else:
            self.statusBar().showMessage(
                "No se pudo quitar el item. Puede requerir permisos de admin.")

    # ---- Actualizador (Homebrew) ----

    def start_scan_updates(self):
        if not hasattr(self, "updater_rows"):
            self.updater_rows = []
        # limpiar filas previas
        for r in self.updater_rows:
            r.setParent(None)
        self.updater_rows = []
        self.updater_empty.setVisible(False)

        if not software_updater.is_brew_installed():
            self.updater_empty.setText(
                "Homebrew no está instalado en esta Mac. Instalalo desde "
                "brew.sh y volvé a intentar. (Homebrew es el gestor de "
                "paquetes más común en macOS.)")
            self.updater_empty.setVisible(True)
            return

        self.action_button.setEnabled(False)
        self.overlay.show_over()
        self.progress_dialog = ProgressDialog(
            "Buscando actualizaciones…", parent=self)
        self.progress_dialog.show()

        self.thread = QThread()
        self.worker = SoftwareUpdaterScanWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(
            lambda m: self.progress_dialog.set_detail(m) if self.progress_dialog else None)
        self.worker.finished.connect(self._on_scan_updates_done)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_scan_updates_done(self, packages):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.overlay.hide()
        self.action_button.setEnabled(True)
        if not packages:
            self.updater_empty.setText(
                "Todos los paquetes de Homebrew están al día. ✓")
            self.updater_empty.setVisible(True)
            self.clean_button.setEnabled(False)
            self.statusBar().showMessage("Homebrew: nada para actualizar.")
            return
        insert_at = self.updater_layout.count() - 1
        for pkg in packages:
            row = OutdatedPackageRow(pkg)
            row.changed.connect(self._update_footer)
            self.updater_layout.insertWidget(insert_at, row)
            self.updater_rows.append(row)
            insert_at += 1
        self.statusBar().showMessage(
            f"{len(packages)} paquete(s) con updates disponibles.")
        self._update_footer()
        if not self.isActiveWindow():
            notify("Actualizaciones disponibles",
                   f"{len(packages)} paquete(s) de Homebrew tienen updates.",
                   subtitle="CleanMyCompu")

    def start_upgrade_selected(self):
        selected_rows = [r for r in self.updater_rows if r.is_selected()]
        if not selected_rows:
            return
        selected_names = [r.pkg["name"] for r in selected_rows]

        # Confirmar
        items = [{"name": r.pkg["name"], "icon": "arrow-up-circle", "bytes": 0}
                 for r in selected_rows]
        dlg = ConfirmDialog(
            title=f"Actualizar {len(selected_names)} paquete(s)",
            body=(f"Se van a actualizar los siguientes paquetes con "
                  "'brew upgrade'. Podés seguir usando la app mientras corre.\n\n"
                  + "\n".join(f"   • {n}" for n in selected_names[:8])
                  + (f"\n   … y {len(selected_names)-8} más" if len(selected_names) > 8 else "")),
            icon_name="download",
            icon_color=Colors.SUCCESS,
            ok_label="Actualizar",
            cancel_label="Cancelar",
            ok_role="positive",
            parent=self,
        )
        if dlg.exec() != QDialog.Accepted:
            return

        self.action_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.overlay.show_over()
        self.progress_dialog = ProgressDialog(
            "Actualizando paquetes…", parent=self)
        self.progress_dialog.show()

        self.thread = QThread()
        self.worker = SoftwareUpgradeWorker(selected_names)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(
            lambda m: self.progress_dialog.set_detail(m) if self.progress_dialog else None)
        self.worker.finished.connect(self._on_upgrade_done)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_upgrade_done(self, result):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.overlay.hide()
        self.action_button.setEnabled(True)
        if result.get("success"):
            if not self.isActiveWindow():
                notify("Actualización completa",
                       "Los paquetes de Homebrew se actualizaron correctamente.",
                       subtitle="CleanMyCompu", sound=True)
            InfoDialog(
                title="Actualización completa",
                body="Todos los paquetes seleccionados se actualizaron. "
                     "Buscá de nuevo para ver si quedó algo por hacer.",
                icon_name="check-circle", icon_color=Colors.SUCCESS,
                parent=self,
            ).exec()
            # Re-scan para refrescar la lista
            self.start_scan_updates()
        else:
            InfoDialog(
                title="Actualización incompleta",
                body=("Algo falló durante 'brew upgrade':\n\n"
                      + (result.get("output", "")[-600:] or "sin detalles")),
                icon_name="alert-triangle", icon_color=Colors.WARNING,
                parent=self,
            ).exec()

    # ---- Memoria ----

    def _refresh_memory_stats(self):
        try:
            stats = memory_clean.get_memory_stats()
            self.memory_bar.set_stats(stats)
        except Exception:
            pass

    def free_memory(self):
        dlg = ConfirmDialog(
            title="Liberar memoria RAM",
            body=("Vamos a ejecutar el comando 'purge' del sistema con permisos "
                  "de administrador. macOS va a pedirte la contraseña.\n\n"
                  "Esto libera páginas inactivas y comprimidas — es 100% "
                  "seguro, no afecta a apps en uso."),
            icon_name="cpu",
            icon_color=Colors.SUCCESS,
            ok_label="Liberar",
            cancel_label="Cancelar",
            ok_role="positive",
            parent=self,
        )
        if dlg.exec() != QDialog.Accepted:
            return
        self.overlay.show_over()
        self.progress_dialog = ProgressDialog(
            "Liberando memoria…", parent=self)
        self.progress_dialog.show()
        QApplication.processEvents()

        result = memory_clean.free_memory(
            on_status=lambda m: (
                self.progress_dialog.set_detail(m) if self.progress_dialog else None,
                QApplication.processEvents(),
            ))

        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.overlay.hide()

        if result.get("cancelled"):
            return  # user canceló password prompt
        if result.get("error"):
            InfoDialog(
                title="No se pudo liberar la memoria",
                body=f"Error: {result['error'][:400]}",
                icon_name="alert-triangle", icon_color=Colors.WARNING,
                parent=self,
            ).exec()
            return

        # Refrescar el bar
        self._refresh_memory_stats()
        freed = result.get("freed", 0)
        before_inactive = result.get("before", {}).get("inactive", 0)
        after_inactive = result.get("after", {}).get("inactive", 0)
        released_inactive = max(0, before_inactive - after_inactive)
        InfoDialog(
            title="Memoria liberada",
            body=(f"RAM libre creció {human_bytes(freed)}.\n"
                  f"Páginas inactivas liberadas: {human_bytes(released_inactive)}."),
            icon_name="check-circle", icon_color=Colors.SUCCESS, parent=self,
        ).exec()
        if not self.isActiveWindow():
            notify("Memoria liberada",
                   f"RAM libre creció {human_bytes(freed)}.",
                   subtitle="CleanMyCompu")

    # ---- Update checker (nueva versión de CleanMyCompu) ----

    def _schedule_update_check(self):
        """Se llama al startup — chequea si hay update en background 2s después."""
        QTimer.singleShot(2000, self._start_update_check)

    def _start_update_check(self):
        self._update_thread = QThread()
        self._update_worker = UpdateCheckWorker()
        self._update_worker.moveToThread(self._update_thread)
        self._update_thread.started.connect(self._update_worker.run)
        self._update_worker.finished.connect(self._on_update_check_done)
        self._update_worker.finished.connect(self._update_thread.quit)
        self._update_worker.finished.connect(self._update_worker.deleteLater)
        self._update_thread.finished.connect(self._update_thread.deleteLater)
        self._update_thread.start()

    def _on_update_check_done(self, result):
        if not result:
            return  # sin update disponible o falló la consulta (silencioso)
        self._available_update = result
        # Notificación nativa
        notify(f"CleanMyCompu {result['version']} disponible",
               "Hacé clic en el link del sidebar para descargar.",
               subtitle=f"Tenés v{result['current']}")
        # Actualizar sidebar con indicador clickeable de nueva versión
        self.storage_bar.show_update(result["version"], result.get("url", ""))

    # ---- Rendimiento (suspender procesos) ----

    def start_perf_scan(self):
        if not performance.is_available():
            InfoDialog(
                title="psutil no está instalado",
                body="La sección Rendimiento necesita la librería 'psutil'. "
                     "Instalá con: pip install psutil",
                icon_name="alert-triangle", icon_color=Colors.WARNING, parent=self,
            ).exec()
            return

        for r in self.perf_rows:
            r.setParent(None)
        self.perf_rows = []
        self.perf_empty.setVisible(False)

        self.overlay.show_over()
        self.progress_dialog = ProgressDialog("Buscando procesos…", parent=self)
        self.progress_dialog.show()

        self.thread = QThread()
        self.worker = ProcessListWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_perf_scan_done)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_perf_scan_done(self, procs):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.overlay.hide()

        # Actualizar card de memoria
        mem = performance.get_memory_info()
        if mem["total"] > 0:
            pct = mem.get("percent", (mem["used"] / mem["total"]) * 100)
            self.perf_memory_text.setText(
                f"En uso: {human_bytes(mem['used'])} de {human_bytes(mem['total'])} "
                f"({pct:.0f}%)  ·  Libre: {human_bytes(mem['free'])}"
            )

        if not procs:
            self.perf_empty.set_body(
                "No se detectaron procesos con más de 30 MB de RAM. "
                "(O psutil no tiene permisos suficientes.)")
            self.perf_empty.setVisible(True)
            self._refresh_action_button_visibility()
            return

        # Insertar filas ANTES del stretch (índice = count - 1 después del empty)
        insert_at = self.perf_layout.indexOf(self.perf_empty)
        if insert_at < 0:
            insert_at = self.perf_layout.count() - 1
        for proc in procs[:100]:
            row = ProcessRow(proc)
            row.action_requested.connect(self._on_perf_action)
            self.perf_layout.insertWidget(insert_at, row)
            self.perf_rows.append(row)
            insert_at += 1
        total_mb = performance.total_memory_used_by_processes(procs)
        self.statusBar().showMessage(
            f"{len(procs)} procesos consumiendo {total_mb:.0f} MB de RAM en total.")
        self._refresh_action_button_visibility()

    def _on_perf_action(self, pid: int, action: str):
        ok = False
        if action == "suspend":
            ok = performance.suspend(pid)
        elif action == "resume":
            ok = performance.resume(pid)
        elif action == "kill":
            ok = performance.kill(pid)
        if not ok:
            self.statusBar().showMessage(
                f"No se pudo {action} PID {pid} (proceso protegido o sin permisos).")
        # Re-escanear para refrescar
        self.start_perf_scan()

    # ---- Helpers ----

    def _find_cat(self, cat_id: str):
        return next((c for c in self.categories if c["id"] == cat_id), None)

    def _on_onboarding_dismissed(self):
        """Al presionar 'Entendido' — marcar la sección como visitada y persistir."""
        section = getattr(self, "_pending_visit", None) or self.current_section
        if section:
            self.visited_sections.add(section)
            self.settings.setValue("visited_sections", list(self.visited_sections))


# ============================================================
# Entry point
# ============================================================

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CleanMyCompu")

    font = QFont()
    font.setPointSize(13)
    app.setFont(font)

    icon_path = Path(__file__).parent / "assets" / "app_icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    win = MainWindow()
    win.show()

    try:
        QGuiApplication.styleHints().colorSchemeChanged.connect(
            lambda _: win._apply_theme())
    except Exception:
        pass

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
