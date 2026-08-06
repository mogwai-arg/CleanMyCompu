"""
Diálogos custom para CleanMyCompu.
Reemplazan los QMessageBox nativos con nuestro sistema de diseño.
"""

from typing import Callable, List, Optional

from PySide6.QtCore import Qt, QSize, QTimer, QRectF, Signal
from PySide6.QtGui import QIcon, QPainter, QPen, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame, QWidget, QProgressBar,
)

from ui_theme import Spacing, Type, Colors, is_dark_mode
from icons import make_icon_pixmap


# ============================================================
# CircularSpinner — anillo animado tipo CCleaner
# ============================================================

class CircularSpinner(QWidget):
    """Anillo animado (arco que rota) — reemplaza la barra de progreso lineal."""

    def __init__(self, size: int = 120, color: Optional[str] = None,
                 track_color: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._pen_width = max(6, size // 15)
        self._color = QColor(color or Colors.SUCCESS)
        self._track = QColor(track_color or (
            Colors.BORDER_DARK if is_dark_mode() else Colors.BORDER_LIGHT))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)  # ~33 fps

    def _tick(self):
        self._angle = (self._angle + 6) % 360
        self.update()

    def stop(self):
        self._timer.stop()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pad = self._pen_width // 2 + 2
        rect = QRectF(pad, pad, self.width() - pad * 2, self.height() - pad * 2)
        # Track (círculo tenue)
        pen_track = QPen(self._track, self._pen_width, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen_track)
        p.drawArc(rect, 0, 360 * 16)
        # Arco activo (rotando)
        pen_arc = QPen(self._color, self._pen_width, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen_arc)
        p.drawArc(rect, -self._angle * 16, 110 * 16)


def _human_bytes(n: float) -> str:
    if n < 1024:
        return f"{int(n)} B"
    for unit in ("KB", "MB", "GB", "TB"):
        n /= 1024
        if n < 1024:
            return f"{n:.1f} {unit}"
    return f"{n:.1f} PB"


def _icon_color() -> str:
    return Colors.TEXT_DARK if is_dark_mode() else Colors.TEXT_LIGHT


# ============================================================
# Estilo base compartido por los diálogos
# ============================================================

def _dialog_stylesheet() -> str:
    C = Colors
    S = Spacing
    T = Type
    dark = is_dark_mode()
    bg = C.BG_DARK if dark else C.BG_LIGHT
    surface = C.SURFACE_DARK if dark else C.SURFACE_LIGHT
    border = C.BORDER_DARK if dark else C.BORDER_LIGHT
    text = C.TEXT_DARK if dark else C.TEXT_LIGHT
    text_sec = C.TEXT_SEC_DARK if dark else C.TEXT_SEC_LIGHT
    warning_bg = "#FFF6E5" if not dark else "#3A2E14"
    warning_text = "#8A5A00" if not dark else "#FFD489"
    return f"""
        QDialog {{ background: {bg}; }}
        #dlg-header {{ background: {bg}; border-bottom: 1px solid {border}; }}
        #dlg-title {{
            font-size: {T.XXL}px; font-weight: 700; color: {text};
            background: transparent; letter-spacing: -0.01em;
        }}
        #dlg-subtitle {{
            font-size: {T.MD}px; color: {text_sec}; background: transparent;
        }}
        #dlg-scroll {{ background: {bg}; border: none; }}
        #dlg-scroll QScrollBar:vertical {{ background: transparent; width: 8px; }}
        #dlg-scroll QScrollBar::handle:vertical {{
            background: {border}; border-radius: 4px; min-height: 30px;
        }}
        #dlg-item {{
            background: {surface}; border: 1px solid {border}; border-radius: 6px;
        }}
        #dlg-item-name {{
            font-size: {T.MD}px; color: {text}; background: transparent;
        }}
        #dlg-item-size {{
            font-size: {T.MD}px; color: {text_sec}; font-weight: 600;
            background: transparent;
        }}
        #dlg-note {{
            background: {warning_bg}; color: {warning_text};
            font-size: {T.SM}px; padding: {S.MD}px {S.LG}px; border-radius: 6px;
        }}
        #dlg-success-note {{
            background: {"#E5F7EA" if not dark else "#1E3A24"};
            color: {"#1F7A35" if not dark else "#7FDD97"};
            font-size: {T.MD}px; padding: {S.MD}px {S.LG}px; border-radius: 6px;
        }}
        #dlg-footer {{ background: {bg}; border-top: 1px solid {border}; }}
        #dlg-body {{
            font-size: {T.MD}px; color: {text}; background: transparent;
        }}
    """


# ============================================================
# ConfirmCleanDialog
# ============================================================

class ConfirmCleanDialog(QDialog):
    """
    Confirmación previa a borrar.
    categories_with_sizes: lista de dicts con keys 'name', 'icon' (nombre de icons.ICONS), 'bytes'.
    """
    def __init__(self, categories_with_sizes: list, total_bytes: int, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Confirmar limpieza")
        self.setMinimumWidth(500)
        self.setMinimumHeight(380)
        self.setStyleSheet(_dialog_stylesheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("dlg-header")
        hh = QHBoxLayout(header)
        hh.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.LG)
        hh.setSpacing(Spacing.LG)

        warn = QLabel()
        warn.setPixmap(make_icon_pixmap("alert-triangle", size=28,
                                        color=Colors.WARNING))
        warn.setFixedSize(32, 32)
        warn.setAlignment(Qt.AlignTop)
        hh.addWidget(warn)

        title_col = QVBoxLayout()
        title_col.setSpacing(Spacing.XS)
        title = QLabel(f"¿Liberar {_human_bytes(total_bytes)}?")
        title.setObjectName("dlg-title")
        title.setWordWrap(True)
        subtitle = QLabel("Se van a borrar permanentemente los archivos de estas categorías:")
        subtitle.setObjectName("dlg-subtitle")
        subtitle.setWordWrap(True)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        hh.addLayout(title_col, stretch=1)

        root.addWidget(header)

        # Lista scrollable
        scroll = QScrollArea()
        scroll.setObjectName("dlg-scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        list_wrap = QWidget()
        lv = QVBoxLayout(list_wrap)
        lv.setContentsMargins(Spacing.XL, Spacing.MD, Spacing.XL, Spacing.LG)
        lv.setSpacing(Spacing.XS)
        for c in categories_with_sizes:
            lv.addWidget(self._build_item_row(c))
        lv.addStretch(1)
        scroll.setWidget(list_wrap)
        root.addWidget(scroll, stretch=1)

        # Nota
        note_wrap = QWidget()
        nw = QVBoxLayout(note_wrap)
        nw.setContentsMargins(Spacing.XL, Spacing.SM, Spacing.XL, Spacing.MD)
        note = QLabel(
            "Los archivos de caché los recrean las apps cuando los necesitan. "
            "Esta acción no se puede deshacer."
        )
        note.setObjectName("dlg-note")
        note.setWordWrap(True)
        nw.addWidget(note)
        root.addWidget(note_wrap)

        # Footer
        footer = QWidget()
        footer.setObjectName("dlg-footer")
        fh = QHBoxLayout(footer)
        fh.setContentsMargins(Spacing.XL, Spacing.LG, Spacing.XL, Spacing.LG)
        fh.setSpacing(Spacing.MD)
        fh.addStretch(1)
        cancel = QPushButton("Cancelar")
        cancel.setProperty("role", "secondary")
        cancel.clicked.connect(self.reject)
        confirm = QPushButton(f"Limpiar {_human_bytes(total_bytes)}")
        confirm.setProperty("role", "destructive")
        confirm.setDefault(True)
        confirm.clicked.connect(self.accept)
        fh.addWidget(cancel)
        fh.addWidget(confirm)
        root.addWidget(footer)

    def _build_item_row(self, cat: dict) -> QWidget:
        row = QFrame()
        row.setObjectName("dlg-item")
        h = QHBoxLayout(row)
        h.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        h.setSpacing(Spacing.MD)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon_pixmap(cat.get("icon", "ghost"),
                                            size=18, color=_icon_color()))
        icon_lbl.setFixedSize(24, 24)
        icon_lbl.setAlignment(Qt.AlignCenter)

        name = QLabel(cat["name"])
        name.setObjectName("dlg-item-name")

        size = QLabel(_human_bytes(cat["bytes"]))
        size.setObjectName("dlg-item-size")
        size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        h.addWidget(icon_lbl)
        h.addWidget(name, stretch=1)
        h.addWidget(size)
        return row


# ============================================================
# InfoDialog — reemplazo del QMessageBox.information
# ============================================================

class InfoDialog(QDialog):
    """
    Diálogo de éxito/info con ícono grande centrado y estilo celebratorio.
    """
    def __init__(self, title: str, body: str, icon_name: str = "check-circle",
                 icon_color: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self.setMinimumHeight(340)
        self.setStyleSheet(_dialog_stylesheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(Spacing.XXL, Spacing.XXL, Spacing.XXL, Spacing.LG)
        root.setSpacing(Spacing.MD)

        # Ícono grande centrado con círculo de fondo tenue
        color = icon_color or Colors.SUCCESS
        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon_pixmap(icon_name, size=64, color=color))
        icon_lbl.setFixedSize(96, 96)
        icon_lbl.setAlignment(Qt.AlignCenter)
        # Fondo siempre negro (matches el logo), el ícono color contrasta
        icon_lbl.setStyleSheet(
            f"background: {Colors.TEXT_LIGHT}; border-radius: 48px;")
        icon_row = QHBoxLayout()
        icon_row.addStretch(1)
        icon_row.addWidget(icon_lbl)
        icon_row.addStretch(1)
        root.addLayout(icon_row)

        # Título centrado, grande
        title_lbl = QLabel(title)
        title_lbl.setObjectName("dlg-title")
        title_lbl.setWordWrap(True)
        title_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(title_lbl)

        # Cuerpo centrado
        body_lbl = QLabel(body)
        body_lbl.setObjectName("dlg-body")
        body_lbl.setWordWrap(True)
        body_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(body_lbl)

        root.addStretch(1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("Aceptar")
        ok.setProperty("role", "primary")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        footer.addWidget(ok)
        footer.addStretch(1)
        root.addLayout(footer)


# ============================================================
# ProgressDialog — muestra qué archivo se está borrando
# ============================================================

class RunningProcessesDialog(QDialog):
    """
    Diálogo que muestra procesos relacionados con una app que se está por desinstalar.
    Botones: Cancelar / Cerrar todo y continuar.

    Uso:
        d = RunningProcessesDialog("EaseUS RecExperts", procs, parent=self)
        if d.exec() == QDialog.Accepted:
            # user pidió cerrar todo
    """

    def __init__(self, app_name: str, processes: list, parent=None,
                 force_variant: bool = False):
        """
        force_variant: si True, es la 2da pasada — algo quedó atrás y se ofrece
                       forzar cierre (SIGKILL) para reintentar.
        """
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(f"{app_name} sigue corriendo")
        self.setMinimumWidth(500)
        self.setMinimumHeight(360)
        self.setStyleSheet(_dialog_stylesheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("dlg-header")
        hh = QHBoxLayout(header)
        hh.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.LG)
        hh.setSpacing(Spacing.LG)
        icon = QLabel()
        icon.setPixmap(make_icon_pixmap("alert-triangle", size=28,
                                        color=Colors.WARNING))
        icon.setFixedSize(32, 32)
        icon.setAlignment(Qt.AlignTop)
        hh.addWidget(icon)
        title_col = QVBoxLayout()
        title_col.setSpacing(Spacing.XS)
        t = QLabel(f"{app_name} sigue corriendo")
        t.setObjectName("dlg-title")
        t.setWordWrap(True)
        if force_variant:
            sub_text = (f"Algunos archivos quedaron bloqueados porque {len(processes)} "
                        "proceso(s) siguen corriendo. Podemos forzar el cierre (SIGKILL) "
                        "y reintentar la desinstalación.")
        else:
            sub_text = (f"Encontramos {len(processes)} proceso(s) relacionados. "
                        "Para desinstalar limpiamente hay que cerrarlos primero. "
                        "¿Los cerramos ahora?")
        s = QLabel(sub_text)
        s.setObjectName("dlg-subtitle")
        s.setWordWrap(True)
        title_col.addWidget(t)
        title_col.addWidget(s)
        hh.addLayout(title_col, stretch=1)
        root.addWidget(header)

        # Lista scrollable de procesos
        scroll = QScrollArea()
        scroll.setObjectName("dlg-scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        wrap = QWidget()
        lv = QVBoxLayout(wrap)
        lv.setContentsMargins(Spacing.XL, Spacing.MD, Spacing.XL, Spacing.LG)
        lv.setSpacing(Spacing.XS)
        for p in processes:
            lv.addWidget(self._build_proc_row(p))
        lv.addStretch(1)
        scroll.setWidget(wrap)
        root.addWidget(scroll, stretch=1)

        # Footer
        footer = QWidget()
        footer.setObjectName("dlg-footer")
        fh = QHBoxLayout(footer)
        fh.setContentsMargins(Spacing.XL, Spacing.LG, Spacing.XL, Spacing.LG)
        fh.setSpacing(Spacing.MD)
        fh.addStretch(1)
        cancel = QPushButton("Cancelar")
        cancel.setProperty("role", "secondary")
        cancel.clicked.connect(self.reject)
        label_ok = "Forzar cierre y reintentar" if force_variant else "Cerrar todo y continuar"
        confirm = QPushButton(label_ok)
        confirm.setProperty("role", "destructive")
        confirm.setDefault(True)
        confirm.clicked.connect(self.accept)
        fh.addWidget(cancel)
        fh.addWidget(confirm)
        root.addWidget(footer)

    def _build_proc_row(self, p: dict) -> QWidget:
        row = QFrame()
        row.setObjectName("dlg-item")
        h = QHBoxLayout(row)
        h.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        h.setSpacing(Spacing.MD)
        icon = QLabel()
        icon.setPixmap(make_icon_pixmap("power", size=16, color=_icon_color()))
        icon.setFixedSize(20, 20)
        icon.setAlignment(Qt.AlignCenter)
        name = QLabel(p["name"])
        name.setObjectName("dlg-item-name")
        pid = QLabel(f"pid {p['pid']}")
        pid.setObjectName("dlg-item-size")
        pid.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(icon)
        h.addWidget(name, stretch=1)
        h.addWidget(pid)
        return row


class ConfirmDialog(QDialog):
    """
    Diálogo genérico de confirmación con ícono grande + texto + 2 botones.
    Uso: si exec() == QDialog.Accepted, el usuario confirmó.
    """
    def __init__(self, title: str, body: str,
                 icon_name: str = "alert-triangle",
                 icon_color: Optional[str] = None,
                 ok_label: str = "Continuar",
                 cancel_label: str = "Cancelar",
                 ok_role: str = "destructive",
                 parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self.setMinimumHeight(320)
        self.setStyleSheet(_dialog_stylesheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(Spacing.XXL, Spacing.XXL, Spacing.XXL, Spacing.LG)
        root.setSpacing(Spacing.MD)

        # Ícono grande centrado con círculo de fondo tenue
        color = icon_color or Colors.WARNING
        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon_pixmap(icon_name, size=48, color=color))
        icon_lbl.setFixedSize(80, 80)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(f"background: {Colors.TEXT_LIGHT}; border-radius: 40px;")
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(icon_lbl)
        row.addStretch(1)
        root.addLayout(row)

        # Título centrado
        t = QLabel(title)
        t.setObjectName("dlg-title")
        t.setWordWrap(True)
        t.setAlignment(Qt.AlignCenter)
        root.addWidget(t)

        # Body centrado
        b = QLabel(body)
        b.setObjectName("dlg-body")
        b.setWordWrap(True)
        b.setAlignment(Qt.AlignCenter)
        root.addWidget(b)

        root.addStretch(1)

        # Botones
        footer = QHBoxLayout()
        footer.addStretch(1)
        cancel = QPushButton(cancel_label)
        cancel.setProperty("role", "secondary")
        cancel.clicked.connect(self.reject)
        ok = QPushButton(ok_label)
        ok.setProperty("role", ok_role)
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        footer.addWidget(cancel)
        footer.addWidget(ok)
        footer.addStretch(1)
        root.addLayout(footer)


class ProgressDialog(QDialog):
    """
    Diálogo modal con spinner circular + título + detalle.
    Opcional: botón Cancelar que emite `cancelled` cuando el usuario quiere parar.
    """
    cancelled = Signal()

    def __init__(self, title: str = "Trabajando…", parent=None,
                 spinner_color: Optional[str] = None,
                 cancellable: bool = False):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self.setMinimumHeight(340)
        self.setStyleSheet(_dialog_stylesheet())
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)
        self.setWindowFlag(Qt.WindowMinMaxButtonsHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(Spacing.XXL, Spacing.XL, Spacing.XXL, Spacing.XL)
        root.setSpacing(Spacing.LG)

        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("dlg-title")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(self.title_lbl)

        # Spinner circular animado (verde por default — nunca azul)
        spin_row = QHBoxLayout()
        spin_row.addStretch(1)
        default_spinner = (Colors.SUCCESS_DARK if is_dark_mode() else Colors.SUCCESS)
        self.spinner = CircularSpinner(size=120, color=spinner_color or default_spinner)
        spin_row.addWidget(self.spinner)
        spin_row.addStretch(1)
        root.addLayout(spin_row)

        self.detail_lbl = QLabel("Preparando…")
        self.detail_lbl.setObjectName("dlg-subtitle")
        self.detail_lbl.setWordWrap(True)
        self.detail_lbl.setAlignment(Qt.AlignCenter)
        self.detail_lbl.setMinimumHeight(20)
        root.addWidget(self.detail_lbl)

        # Botón cancelar (opcional)
        if cancellable:
            btn_row = QHBoxLayout()
            btn_row.addStretch(1)
            self.cancel_btn = QPushButton("Cancelar y usar lo encontrado")
            self.cancel_btn.setProperty("role", "secondary")
            self.cancel_btn.clicked.connect(self._on_cancel_clicked)
            btn_row.addWidget(self.cancel_btn)
            btn_row.addStretch(1)
            root.addLayout(btn_row)
        else:
            self.cancel_btn = None

    def _on_cancel_clicked(self):
        if self.cancel_btn:
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setText("Cancelando…")
        self.set_detail("Cancelando… guardando resultados encontrados.")
        self.cancelled.emit()

    def set_detail(self, text: str):
        if len(text) > 80:
            text = text[:38] + " … " + text[-38:]
        self.detail_lbl.setText(text)

    def set_title(self, text: str):
        self.title_lbl.setText(text)

    def close(self):
        try:
            self.spinner.stop()
        except Exception:
            pass
        super().close()


class DriveSelectorDialog(QDialog):
    """
    Diálogo para elegir en qué carpetas/discos buscar antes de arrancar el scan.
    """
    def __init__(self, title: str, subtitle: str, roots: list, parent=None):
        """
        roots: lista de dicts {label, path, default_checked (bool)}
        """
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self.setStyleSheet(_dialog_stylesheet())
        self._roots = roots
        self._checks = []

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(Spacing.XXL, Spacing.XL, Spacing.XXL, Spacing.LG)
        root_layout.setSpacing(Spacing.MD)

        t = QLabel(title)
        t.setObjectName("dlg-title")
        root_layout.addWidget(t)

        s = QLabel(subtitle)
        s.setObjectName("dlg-subtitle")
        s.setWordWrap(True)
        root_layout.addWidget(s)

        # Checkbox por root
        from PySide6.QtWidgets import QCheckBox
        for r in roots:
            row = QHBoxLayout()
            cb = QCheckBox(r["label"])
            cb.setChecked(r.get("default_checked", True))
            self._checks.append((cb, r["path"]))
            row.addWidget(cb)
            row.addStretch(1)
            path_lbl = QLabel(str(r["path"]))
            path_lbl.setObjectName("dlg-subtitle")
            row.addWidget(path_lbl)
            root_layout.addLayout(row)

        root_layout.addStretch(1)

        # Botones
        footer = QHBoxLayout()
        footer.addStretch(1)
        cancel = QPushButton("Cancelar")
        cancel.setProperty("role", "secondary")
        cancel.clicked.connect(self.reject)
        go = QPushButton("Buscar")
        go.setProperty("role", "positive")
        go.setDefault(True)
        go.clicked.connect(self.accept)
        footer.addWidget(cancel)
        footer.addWidget(go)
        root_layout.addLayout(footer)

    def selected_paths(self) -> list:
        return [path for cb, path in self._checks if cb.isChecked()]
