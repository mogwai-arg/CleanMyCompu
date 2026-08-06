"""
Widget de confetti — animación celebratoria cuando el usuario libera espacio.

Se superpone sobre la ventana principal, ignora eventos de mouse (para no
bloquear la UI), y se autodestruye después de ~3 segundos.
"""

import random

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QBrush
from PySide6.QtWidgets import QWidget


# Colores festivos — mezcla vibrante que evita el azul (por el design system)
_CONFETTI_COLORS = [
    "#34C759",  # verde éxito
    "#30D158",  # verde brillante
    "#FF9500",  # naranja
    "#FFCC00",  # amarillo
    "#FF3B30",  # rojo
    "#FF2D55",  # rosa
    "#AF52DE",  # violeta
    "#FF6B35",  # naranja fuego
]


class Confetti(QWidget):
    """
    Overlay animado con partículas físicas. Crear con:
        c = Confetti(parent)
        c.show()
    Se autodestruye al terminar la animación.
    """

    def __init__(self, parent: QWidget, particle_count: int = 180,
                 duration_ms: int = 3200):
        super().__init__(parent)
        # No bloquear clicks — el usuario puede seguir usando la app
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_NoSystemBackground)
        # Cubrir todo el parent
        self.setGeometry(parent.rect())

        w = max(1, self.width())
        # Partículas emitidas en 3 "burst" desde arriba, esparcidas horizontalmente
        self.particles = []
        for _ in range(particle_count):
            self.particles.append({
                "x": random.uniform(0, w),
                "y": random.uniform(-80, -10),
                # velocidad inicial: mayormente hacia abajo con variación lateral
                "vx": random.uniform(-3.5, 3.5),
                "vy": random.uniform(-1, 4),
                "size": random.uniform(6, 12),
                "color": QColor(random.choice(_CONFETTI_COLORS)),
                "rot": random.uniform(0, 360),
                "vrot": random.uniform(-12, 12),
                "shape": random.choice(["rect", "circle", "rect"]),  # más rectángulos
                "sway": random.uniform(0.02, 0.06),  # oscilación tipo hoja
                "sway_phase": random.uniform(0, 6.28),
            })

        self._frame = 0
        self._fps_ms = 16  # ~60fps
        self._duration_frames = duration_ms // self._fps_ms
        self._fade_start = int(self._duration_frames * 0.65)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self._fps_ms)

    def _tick(self):
        h = self.height()
        for p in self.particles:
            # Gravedad + fricción ligera
            p["vy"] += 0.14
            p["vx"] *= 0.995
            p["vy"] *= 0.995
            # Oscilación lateral (efecto "cae en zigzag")
            p["vx"] += p["sway"] * (0.5 - random.random())
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["rot"] += p["vrot"]
            # Si sale por abajo, no volver a pintar
            if p["y"] > h + 50:
                p["y"] = h + 100

        self._frame += 1
        self.update()

        if self._frame >= self._duration_frames:
            self._timer.stop()
            self.deleteLater()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)

        # Fade en el último tercio de la animación
        if self._frame >= self._fade_start:
            span = max(1, self._duration_frames - self._fade_start)
            fade = 1.0 - (self._frame - self._fade_start) / span
            fade = max(0.0, min(1.0, fade))
        else:
            fade = 1.0

        h = self.height()
        for particle in self.particles:
            y = particle["y"]
            if y < -30 or y > h + 30:
                continue
            color = QColor(particle["color"])
            color.setAlphaF(fade * 0.95)
            p.setBrush(QBrush(color))
            p.save()
            p.translate(particle["x"], y)
            p.rotate(particle["rot"])
            s = particle["size"]
            if particle["shape"] == "rect":
                p.drawRect(QRectF(-s / 2, -s / 3, s, s * 0.65))
            else:
                p.drawEllipse(QPointF(0, 0), s / 2, s / 2)
            p.restore()

        p.end()
