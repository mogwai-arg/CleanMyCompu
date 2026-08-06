"""
Íconos flat estilo Lucide/SF Symbols.
SVGs monocromáticos con stroke="currentColor" — reemplazamos ese literal
por el color deseado antes de renderizar.

Uso desde otros módulos:
    from icons import make_icon_pixmap, make_logo_pixmap
    label.setPixmap(make_icon_pixmap("stethoscope", size=24, color="#1D1D1F"))
"""

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QPainter, QPixmap, QColor
from PySide6.QtSvg import QSvgRenderer


# stroke-width elegido para verse bien a 20-24 px
_TPL = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" '
    'stroke-linecap="round" stroke-linejoin="round">{}</svg>'
)


ICONS = {
    "stethoscope": _TPL.format(
        '<path d="M11 2v2"/>'
        '<path d="M5 2v2"/>'
        '<path d="M5 3H4a2 2 0 0 0-2 2v4a6 6 0 0 0 12 0V5a2 2 0 0 0-2-2h-1"/>'
        '<path d="M8 15a6 6 0 0 0 12 0v-3"/>'
        '<circle cx="20" cy="10" r="2"/>'
    ),
    "sparkles": _TPL.format(
        '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/>'
        '<path d="M20 3v4"/><path d="M22 5h-4"/>'
        '<path d="M4 17v2"/><path d="M5 18H3"/>'
    ),
    "trash": _TPL.format(
        '<path d="M3 6h18"/>'
        '<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
        '<path d="M19 6l-1.5 14a2 2 0 0 1-2 1.8h-7a2 2 0 0 1-2-1.8L5 6"/>'
        '<line x1="10" x2="10" y1="11" y2="17"/>'
        '<line x1="14" x2="14" y1="11" y2="17"/>'
    ),
    "file-text": _TPL.format(
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
        '<line x1="8" x2="16" y1="13" y2="13"/>'
        '<line x1="8" x2="16" y1="17" y2="17"/>'
        '<line x1="8" x2="10" y1="9" y2="9"/>'
    ),
    "image": _TPL.format(
        '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/>'
        '<circle cx="9" cy="9" r="2"/>'
        '<path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>'
    ),
    "alert-triangle": _TPL.format(
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
        '<line x1="12" x2="12" y1="9" y2="13"/>'
        '<line x1="12" x2="12.01" y1="17" y2="17"/>'
    ),
    "globe": _TPL.format(
        '<circle cx="12" cy="12" r="10"/>'
        '<path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/>'
        '<line x1="2" x2="22" y1="12" y2="12"/>'
    ),
    "palette": _TPL.format(
        '<circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/>'
        '<circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/>'
        '<circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/>'
        '<circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/>'
        '<path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>'
    ),
    "box": _TPL.format(
        '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/>'
        '<path d="m3.3 7 8.7 5 8.7-5"/>'
        '<path d="M12 22V12"/>'
    ),
    "hard-drive": _TPL.format(
        '<line x1="22" x2="2" y1="12" y2="12"/>'
        '<path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>'
        '<line x1="6" x2="6.01" y1="16" y2="16"/>'
        '<line x1="10" x2="10.01" y1="16" y2="16"/>'
    ),
    "ghost": _TPL.format(
        '<path d="M9 10h.01"/><path d="M15 10h.01"/>'
        '<path d="M12 2a8 8 0 0 0-8 8v12l3-3 2.5 2.5L12 19l2.5 2.5L17 19l3 3V10a8 8 0 0 0-8-8z"/>'
    ),
    "code": _TPL.format(
        '<polyline points="16 18 22 12 16 6"/>'
        '<polyline points="8 6 2 12 8 18"/>'
    ),
    "smartphone": _TPL.format(
        '<rect width="14" height="20" x="5" y="2" rx="2" ry="2"/>'
        '<path d="M12 18h.01"/>'
    ),
    "coffee": _TPL.format(
        '<path d="M17 8h1a4 4 0 1 1 0 8h-1"/>'
        '<path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z"/>'
        '<line x1="6" x2="6" y1="2" y2="4"/>'
        '<line x1="10" x2="10" y1="2" y2="4"/>'
        '<line x1="14" x2="14" y1="2" y2="4"/>'
    ),
    "terminal": _TPL.format(
        '<polyline points="4 17 10 11 4 5"/>'
        '<line x1="12" x2="20" y1="19" y2="19"/>'
    ),
    "copy": _TPL.format(
        '<rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>'
        '<path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>'
    ),
    "hammer": _TPL.format(
        '<path d="m15 12-8.5 8.5c-.83.83-2.17.83-3 0 0 0 0 0 0 0a2.12 2.12 0 0 1 0-3L12 9"/>'
        '<path d="M17.64 15 22 10.64"/>'
        '<path d="m20.91 11.7-1.25-1.25c-.6-.6-.93-1.4-.93-2.25v-.86L16.01 4.6a5.56 5.56 0 0 0-3.94-1.64H9l.92.82A6.18 6.18 0 0 1 12 8.4v1.56l2 2h2.47l2.26 1.91"/>'
    ),
    "check-circle": _TPL.format(
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
        '<polyline points="22 4 12 14.01 9 11.01"/>'
    ),
    "loader": _TPL.format(
        '<path d="M21 12a9 9 0 1 1-6.219-8.56"/>'
    ),
    "info": _TPL.format(
        '<circle cx="12" cy="12" r="10"/>'
        '<path d="M12 16v-4"/>'
        '<path d="M12 8h.01"/>'
    ),
    "app-window": _TPL.format(
        '<rect x="2" y="4" width="20" height="16" rx="2"/>'
        '<path d="M2 8h20"/>'
        '<path d="M6 4v4"/>'
        '<path d="M10 4v4"/>'
    ),
    "power": _TPL.format(
        '<path d="M12 2v10"/>'
        '<path d="M18.4 6.6a9 9 0 1 1-12.77.04"/>'
    ),
    "clock": _TPL.format(
        '<circle cx="12" cy="12" r="10"/>'
        '<polyline points="12 6 12 12 16 14"/>'
    ),
    "chevron-right": _TPL.format(
        '<polyline points="9 18 15 12 9 6"/>'
    ),
    "search": _TPL.format(
        '<circle cx="11" cy="11" r="8"/>'
        '<line x1="21" x2="16.65" y1="21" y2="16.65"/>'
    ),
    "cpu": _TPL.format(
        '<rect x="4" y="4" width="16" height="16" rx="2"/>'
        '<rect x="9" y="9" width="6" height="6"/>'
        '<path d="M9 2v2"/><path d="M15 2v2"/>'
        '<path d="M9 20v2"/><path d="M15 20v2"/>'
        '<path d="M2 9h2"/><path d="M2 15h2"/>'
        '<path d="M20 9h2"/><path d="M20 15h2"/>'
    ),
    "download": _TPL.format(
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
        '<polyline points="7 10 12 15 17 10"/>'
        '<line x1="12" x2="12" y1="15" y2="3"/>'
    ),
    "refresh-cw": _TPL.format(
        '<path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>'
        '<path d="M3 3v5h5"/>'
        '<path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>'
        '<path d="M16 16h5v5"/>'
    ),
    "arrow-up-circle": _TPL.format(
        '<circle cx="12" cy="12" r="10"/>'
        '<polyline points="16 12 12 8 8 12"/>'
        '<line x1="12" x2="12" y1="16" y2="8"/>'
    ),
}


def render_svg_pixmap(svg_data: str, size: int = 24) -> QPixmap:
    """Convierte una string SVG en un QPixmap del tamaño pedido."""
    # Multiplicamos por devicePixelRatio para que se vea nítido en pantallas retina
    scale = 2  # asumimos retina — en Mac es lo normal
    render_size = size * scale
    renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
    pm = QPixmap(render_size, render_size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, render_size, render_size))
    painter.end()
    pm.setDevicePixelRatio(scale)
    return pm


def make_icon_pixmap(name: str, size: int = 20, color: str = "#1D1D1F") -> QPixmap:
    """Renderiza un ícono del catálogo ICONS con el color y tamaño dados."""
    svg = ICONS.get(name)
    if svg is None:
        svg = ICONS["ghost"]  # fallback visible pero raro para detectar iconos faltantes
    svg = svg.replace("currentColor", color)
    return render_svg_pixmap(svg, size=size)


def make_logo_pixmap(size: int = 32, bg: str = "#1D1D1F", fg: str = "#FFFFFF",
                     radius_ratio: float = 0.225, padding_ratio: float = 0.0) -> QPixmap:
    """
    Logo: estetoscopio blanco sobre cuadrado negro con puntas redondeadas.

    padding_ratio: 0.0 rellena todo el canvas (útil para sidebar).
                   0.10 = deja 10% de aire alrededor (obligatorio para el .icns
                   de macOS, si no el ícono se ve enorme al lado de otros en el dock).
    radius_ratio:  0.225 replica la curva "superellipse" que usa Apple en macOS 26.
    """
    scale = 2
    render_size = size * scale
    pm = QPixmap(render_size, render_size)
    pm.fill(Qt.transparent)

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    pad = int(render_size * padding_ratio)
    shape_size = render_size - pad * 2

    # Fondo redondeado (con padding externo si aplica)
    painter.setBrush(QColor(bg))
    painter.setPen(Qt.NoPen)
    radius = shape_size * radius_ratio
    painter.drawRoundedRect(pad, pad, shape_size, shape_size, radius, radius)

    # Ícono estetoscopio: 62% del rectángulo interno, centrado
    inner = int(shape_size * 0.62)
    offset_x = pad + (shape_size - inner) // 2
    offset_y = pad + (shape_size - inner) // 2
    svg = ICONS["stethoscope"].replace("currentColor", fg)
    svg = svg.replace('stroke-width="1.75"', 'stroke-width="2"')
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    renderer.render(painter, QRectF(offset_x, offset_y, inner, inner))

    painter.end()
    pm.setDevicePixelRatio(scale)
    return pm
