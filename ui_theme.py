"""
Sistema de diseño para CleanMyCompu.
Todos los valores visuales viven acá — sin números "sueltos" en el resto del código.
"""

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Qt


# ============================================================
# TOKENS
# ============================================================

class Spacing:
    """Grilla de 8pt — nunca usamos valores fuera de esta escala."""
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32
    XXXL = 48


class Radius:
    SM = 6
    MD = 8
    LG = 12


class Type:
    """Escala tipográfica con razón 1.2 (Minor Third)."""
    XS = 11
    SM = 12
    MD = 13   # base
    LG = 15
    XL = 18
    XXL = 22
    HERO = 30


class Colors:
    # 60% — fondo/canvas (neutro)
    BG_LIGHT = "#F5F5F7"
    BG_DARK = "#1C1C1E"

    # 30% — superficies
    SURFACE_LIGHT = "#FFFFFF"
    SURFACE_DARK = "#2C2C2E"
    SIDEBAR_LIGHT = "#ECECEE"
    SIDEBAR_DARK = "#232326"

    # Bordes/separadores
    BORDER_LIGHT = "#DEDEE1"
    BORDER_DARK = "#38383A"

    # Texto
    TEXT_LIGHT = "#1D1D1F"
    TEXT_DARK = "#F5F5F7"
    TEXT_SEC_LIGHT = "#6E6E73"
    TEXT_SEC_DARK = "#98989D"
    # Alias — texto subtle/secundario que se ve bien en ambos modos
    TEXT_SUBTLE = "#6E6E73"

    # 10% — acento (azul macOS)
    ACCENT_LIGHT = "#0071E3"
    ACCENT_HOVER_LIGHT = "#0077ED"
    ACCENT_PRESSED_LIGHT = "#0062C4"
    ACCENT_TINT_LIGHT = "#E4F0FC"

    ACCENT_DARK = "#0A84FF"
    ACCENT_HOVER_DARK = "#409CFF"
    ACCENT_PRESSED_DARK = "#0060C0"
    ACCENT_TINT_DARK = "#0A2540"

    # Semánticos
    SUCCESS = "#34C759"
    SUCCESS_HOVER = "#3ED166"
    SUCCESS_PRESSED = "#2CB14E"
    SUCCESS_DARK = "#30D158"
    SUCCESS_HOVER_DARK = "#4CDD70"
    SUCCESS_PRESSED_DARK = "#28B84A"
    WARNING = "#FF9500"
    DANGER_LIGHT = "#FF3B30"
    DANGER_HOVER_LIGHT = "#FF5147"
    DANGER_DARK = "#FF453A"
    DANGER_HOVER_DARK = "#FF6259"


# ============================================================
# DETECCIÓN DE TEMA
# ============================================================

def is_dark_mode() -> bool:
    """Detecta si macOS está en modo oscuro."""
    try:
        scheme = QGuiApplication.styleHints().colorScheme()
        return scheme == Qt.ColorScheme.Dark
    except Exception:
        return False


# ============================================================
# STYLESHEET GLOBAL (QSS)
# ============================================================

def build_stylesheet(dark: bool = False) -> str:
    """Devuelve el QSS global, con tokens ya resueltos según el tema."""
    C = Colors
    S = Spacing
    R = Radius
    T = Type

    bg = C.BG_DARK if dark else C.BG_LIGHT
    surface = C.SURFACE_DARK if dark else C.SURFACE_LIGHT
    sidebar_bg = C.SIDEBAR_DARK if dark else C.SIDEBAR_LIGHT
    border = C.BORDER_DARK if dark else C.BORDER_LIGHT
    text = C.TEXT_DARK if dark else C.TEXT_LIGHT
    text_sec = C.TEXT_SEC_DARK if dark else C.TEXT_SEC_LIGHT
    accent = C.ACCENT_DARK if dark else C.ACCENT_LIGHT
    accent_hover = C.ACCENT_HOVER_DARK if dark else C.ACCENT_HOVER_LIGHT
    accent_pressed = C.ACCENT_PRESSED_DARK if dark else C.ACCENT_PRESSED_LIGHT
    accent_tint = C.ACCENT_TINT_DARK if dark else C.ACCENT_TINT_LIGHT
    danger = C.DANGER_DARK if dark else C.DANGER_LIGHT
    danger_hover = C.DANGER_HOVER_DARK if dark else C.DANGER_HOVER_LIGHT
    success = C.SUCCESS_DARK if dark else C.SUCCESS
    success_hover = C.SUCCESS_HOVER_DARK if dark else C.SUCCESS_HOVER
    success_pressed = C.SUCCESS_PRESSED_DARK if dark else C.SUCCESS_PRESSED

    return f"""
    /* ---- Global ---- */
    QMainWindow, QWidget {{
        background-color: {bg};
        color: {text};
        font-size: {T.MD}px;
    }}
    QLabel {{
        background: transparent;
        color: {text};
    }}
    QLabel[role="hero"]     {{ font-size: {T.HERO}px; font-weight: 700; letter-spacing: -0.02em; }}
    QLabel[role="h1"]       {{ font-size: {T.XXL}px;  font-weight: 700; letter-spacing: -0.01em; }}
    QLabel[role="h2"]       {{ font-size: {T.XL}px;   font-weight: 600; }}
    QLabel[role="h3"]       {{ font-size: {T.LG}px;   font-weight: 600; }}
    QLabel[role="body"]     {{ font-size: {T.MD}px;   color: {text}; }}
    QLabel[role="secondary"]{{ font-size: {T.SM}px;   color: {text_sec}; }}
    QLabel[role="caption"]  {{ font-size: {T.XS}px;   color: {text_sec}; letter-spacing: 0.06em; text-transform: uppercase; font-weight: 600; }}
    QLabel[role="mono-size"]{{ font-size: {T.LG}px;   font-weight: 600; color: {text}; font-family: "SF Mono, Menlo, monospace"; }}

    /* ---- Sidebar scroll (interno) — scrollbar overlay minimalista ---- */
    #sidebar-scroll {{
        background: transparent;
        border: none;
    }}
    #sidebar-scroll QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 0;
    }}
    #sidebar-scroll QScrollBar::handle:vertical {{
        background: {border};
        border-radius: 3px;
        min-height: 30px;
    }}
    #sidebar-scroll QScrollBar::add-line, #sidebar-scroll QScrollBar::sub-line {{
        height: 0;
    }}
    #sidebar-scroll QScrollBar::add-page, #sidebar-scroll QScrollBar::sub-page {{
        background: transparent;
    }}

    /* ---- Sidebar ---- */
    #sidebar {{
        background-color: {sidebar_bg};
        border: none;
        border-right: 1px solid {border};
    }}
    #sidebar-title {{
        color: {text};
        font-size: {T.XL}px;
        font-weight: 700;
        padding: {S.XL}px {S.LG}px {S.MD}px {S.LG}px;
        background: transparent;
    }}
    #sidebar-caption {{
        color: {text_sec};
        font-size: {T.XS}px;
        font-weight: 600;
        letter-spacing: 0.08em;
        padding: {S.LG}px {S.LG}px {S.SM}px {S.LG}px;
        background: transparent;
    }}
    #sidebar-list {{
        background: transparent;
        border: none;
        outline: none;
        font-size: {T.MD}px;
    }}
    #sidebar-list::item {{
        padding: {S.SM}px {S.MD}px;
        margin: 2px {S.SM}px;
        border-radius: {R.MD}px;
        color: {text};
    }}
    #sidebar-list::item:hover {{
        background: {border};
    }}
    #sidebar-list::item:selected {{
        background: {text};   /* mismo estilo que el logo: negro en light, blanco en dark */
        color: {bg};          /* invertido: blanco en light, negro en dark */
        font-weight: 600;
    }}
    #sidebar-storage {{
        color: {text_sec};
        font-size: {T.SM}px;
        padding: {S.MD}px {S.LG}px {S.LG}px {S.LG}px;
        background: transparent;
    }}

    /* ---- Detail area ---- */
    #detail-scroll {{ background: {bg}; border: none; }}
    #detail-scroll QScrollBar:vertical {{ background: transparent; width: 8px; }}
    #detail-scroll QScrollBar::handle:vertical {{ background: {border}; border-radius: 4px; min-height: 30px; }}
    #detail-scroll QScrollBar::add-line, #detail-scroll QScrollBar::sub-line {{ height: 0; }}

    /* ---- Category row ---- */
    #category-row {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: {R.MD}px;
    }}
    #category-row:hover {{
        border-color: {text_sec};
    }}
    #row-icon {{
        font-size: 24px;
        background: transparent;
    }}
    #row-name {{
        font-size: {T.MD}px;
        font-weight: 600;
        color: {text};
        background: transparent;
    }}
    #row-desc {{
        font-size: {T.SM}px;
        color: {text_sec};
        background: transparent;
    }}
    #row-size {{
        font-size: {T.LG}px;
        font-weight: 600;
        color: {text};
        background: transparent;
    }}
    #row-empty {{
        font-size: {T.SM}px;
        color: {text_sec};
        background: transparent;
        font-style: italic;
    }}

    /* ---- Botones ---- */
    /* ---- Primary: NEGRO (matches el logo y el selected del sidebar) ---- */
    /* Regla del design system: NUNCA usar azul del sistema en botones. */
    QPushButton[role="primary"] {{
        background-color: {text};       /* dark en light-mode, claro en dark-mode */
        color: {bg};                     /* invertido */
        border: none;
        border-radius: {R.MD}px;
        padding: 10px {S.XL}px;
        font-size: {T.MD}px;
        font-weight: 600;
        min-height: 20px;
    }}
    QPushButton[role="primary"]:hover   {{ background-color: {"#333333" if not dark else "#FFFFFF"}; }}
    QPushButton[role="primary"]:pressed {{ background-color: {"#000000" if not dark else "#DDDDE0"}; }}
    QPushButton[role="primary"]:disabled {{ background-color: {border}; color: {text_sec}; }}

    QPushButton[role="destructive"] {{
        background-color: {danger};
        color: white;
        border: none;
        border-radius: {R.MD}px;
        padding: 10px {S.XL}px;
        font-size: {T.MD}px;
        font-weight: 600;
        min-height: 20px;
    }}
    QPushButton[role="destructive"]:hover   {{ background-color: {danger_hover}; }}
    QPushButton[role="destructive"]:disabled {{ background-color: {border}; color: {text_sec}; }}

    /* ---- "Analizar" (verde, principal de acción) ---- */
    QPushButton[role="positive"] {{
        background-color: {success};
        color: white;
        border: none;
        border-radius: {R.MD}px;
        padding: 12px {S.XL}px;
        font-size: {T.LG}px;
        font-weight: 700;
        min-height: 22px;
    }}
    QPushButton[role="positive"]:hover    {{ background-color: {success_hover}; }}
    QPushButton[role="positive"]:pressed  {{ background-color: {success_pressed}; }}
    QPushButton[role="positive"]:disabled {{ background-color: {border}; color: {text_sec}; }}

    QPushButton[role="secondary"] {{
        background-color: transparent;
        color: {text};
        border: 1px solid {border};
        border-radius: {R.MD}px;
        padding: 10px {S.XL}px;
        font-size: {T.MD}px;
        font-weight: 500;
        min-height: 20px;
    }}
    QPushButton[role="secondary"]:hover {{ background-color: {surface}; border-color: {text_sec}; }}

    /* ---- Botón tipo enlace ("no sugerir más", etc.) ---- */
    QPushButton[role="link"] {{
        background: transparent;
        color: {text_sec};
        border: none;
        padding: 2px 6px;
        font-size: {T.SM}px;
        font-weight: 500;
        text-decoration: underline;
        min-height: 0;
    }}
    QPushButton[role="link"]:hover {{ color: {text}; }}

    /* ---- Badges (recomendaciones) ---- */
    QLabel[role="badge-warn"] {{
        background: {"#FFF1D6" if not dark else "#3A2E14"};
        color: {"#8A5A00" if not dark else "#FFCC70"};
        padding: 3px 10px;
        border-radius: 10px;
        font-size: {T.XS}px;
        font-weight: 700;
        letter-spacing: 0.02em;
    }}
    QLabel[role="reason"] {{
        color: {"#8A5A00" if not dark else "#FFCC70"};
        font-size: {T.SM}px;
        background: transparent;
    }}
    #row-recommended {{
        background-color: {surface};
        border: 1px solid {"#FFB020" if not dark else "#FFCC70"};
        border-left: 4px solid {"#FFB020" if not dark else "#FFCC70"};
        border-radius: {R.MD}px;
    }}

    /* ---- Dashboard cards ---- */
    #dash-card {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: {R.LG}px;
    }}
    #dash-card:hover {{
        border-color: {text};
    }}
    #dash-card-name {{
        font-size: {T.LG}px;
        font-weight: 600;
        color: {text};
        background: transparent;
    }}
    #dash-card-status {{
        font-size: {T.SM}px;
        color: {text_sec};
        background: transparent;
    }}
    #dash-card-status-hl {{
        font-size: {T.MD}px;
        font-weight: 700;
        color: {danger};              /* rojo — representa espacio a borrar */
        background: transparent;
    }}

    /* ---- Empty state (centered icon + title + body + CTA) ---- */
    #empty-state {{
        background: transparent;
    }}
    #empty-icon-bg {{
        background: {C.TEXT_LIGHT};   /* negro siempre — matchea logo y diálogos */
        border-radius: 40px;
    }}
    #empty-title {{
        font-size: {T.LG}px;
        font-weight: 700;
        color: {text};
        background: transparent;
    }}
    #empty-body {{
        font-size: {T.MD}px;
        color: {text_sec};
        background: transparent;
    }}

    /* ---- Storage bar (mini progress en sidebar footer) ---- */
    #storage-bar-track {{
        background: {border};
        border-radius: 3px;
        min-height: 6px;
        max-height: 6px;
    }}
    #storage-bar-fill {{
        background: {success};
        border-radius: 3px;
        min-height: 6px;
        max-height: 6px;
    }}
    #storage-bar-fill-warn {{
        background: {"#FF9500"};
        border-radius: 3px;
        min-height: 6px;
        max-height: 6px;
    }}
    #storage-bar-fill-full {{
        background: {danger};
        border-radius: 3px;
        min-height: 6px;
        max-height: 6px;
    }}
    #storage-text {{
        color: {text_sec};
        font-size: {T.SM}px;
        background: transparent;
    }}
    #update-indicator {{
        color: {success};
        font-size: {T.XS}px;
        font-weight: 600;
        background: transparent;
        padding: 6px 0 0 0;
        border-top: 1px solid {border};
        margin-top: 4px;
    }}

    /* ---- ComboBox del SortBar ---- */
    QComboBox {{
        background: {surface};
        border: 1px solid {border};
        border-radius: {R.SM}px;
        padding: 6px 10px;
        font-size: {T.SM}px;
        color: {text};
        min-height: 22px;
    }}
    QComboBox:hover {{ border-color: {text_sec}; }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox QAbstractItemView {{
        background: {surface};
        border: 1px solid {border};
        selection-background-color: {text};
        selection-color: {bg};
        outline: none;
    }}

    /* ---- Search bar en secciones largas ---- */
    #section-search {{
        background: {surface};
        border: 1px solid {border};
        border-radius: {R.MD}px;
        padding: 8px 12px;
        font-size: {T.MD}px;
        color: {text};
        min-height: 20px;
    }}
    #section-search:focus {{
        border-color: {text};
    }}

    /* ---- Onboarding banner (neutral, sin azul) ---- */
    #onboarding-banner {{
        background: {sidebar_bg};
        border: 1px solid {border};
        border-left: 3px solid {text};
        border-radius: {R.MD}px;
    }}
    #onboarding-title {{
        font-size: {T.MD}px;
        font-weight: 700;
        color: {text};
        background: transparent;
    }}
    #onboarding-body {{
        font-size: {T.SM}px;
        color: {text_sec};
        background: transparent;
    }}

    /* ---- Progress bar ---- */
    QProgressBar {{
        background-color: {border};
        border: none;
        border-radius: 3px;
        max-height: 6px;
        min-height: 6px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background-color: {success};   /* verde, no azul */
        border-radius: 3px;
    }}

    /* ---- Status bar ---- */
    QStatusBar {{
        background: {sidebar_bg};
        border-top: 1px solid {border};
        color: {text_sec};
        font-size: {T.SM}px;
    }}
    QStatusBar::item {{ border: none; }}
    """
