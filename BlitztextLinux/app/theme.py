"""Design-System fuer BlitztextLinux (Breeze-Dark / Glass-Idiom).

Uebersetzt das exportierte Blitztext Design System (Tokens, Glass-UI-Kit) in
PyQt6: ein globales QSS-Stylesheet plus das Marken-App-Icon (Mikrofon + Blitz).

Farb- und Radius-Werte stammen 1:1 aus `tokens/colors.css` und
`tokens/spacing.css` des Design-Systems:
  - Breeze-Dark-Flaechen (#1b1e20 / #2a2e32 / #31363b / #41464c)
  - Brand-Amber  --blitz-500 #e0a90f / --blitz-300 #f2cd4f
  - Breeze-Blau  #3daee9 (OS-Akzent, Fokus)
  - Status: idle #2e7d32, recording #c62828, processing #ef6c00, error #757575
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap

# --- Token-Konstanten (aus dem Design-System) -----------------------------
BLITZ_500 = "#e0a90f"
BLITZ_400 = "#ecbb2a"
BLITZ_300 = "#f2cd4f"

BREEZE_VIEW = "#1b1e20"
BREEZE_WINDOW = "#2a2e32"
BREEZE_BUTTON = "#31363b"
BREEZE_BUTTON_HOV = "#3b4045"
BREEZE_LINE = "#41464c"
BREEZE_BLUE = "#3daee9"

APP_TEXT = "#f4f6f8"
APP_TEXT_DIM = "#9ba2ab"

STATE_IDLE = "#2e7d32"
STATE_RECORDING = "#c62828"
STATE_PROCESSING = "#ef6c00"
STATE_ERROR = "#757575"

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


# --- Globales QSS-Stylesheet ----------------------------------------------
# Modernes Breeze-Dark mit weichen Rundungen, dezenten Hairlines und einem
# Breeze-Blau-Fokusring. Bewusst zurueckhaltend, damit es im KDE-Tray sauber
# wirkt und Dialoge (Einstellungen, Verlauf) konsistent aussehen.
APP_QSS = f"""
* {{
    color: {APP_TEXT};
    font-size: 14px;
}}

QWidget {{
    background-color: {BREEZE_WINDOW};
}}

QLabel {{
    background: transparent;
}}

/* Standard-Buttons: weiche Rundungen statt kantiger Breeze-Defaults */
QPushButton {{
    background-color: {BREEZE_BUTTON};
    border: 1px solid {BREEZE_LINE};
    border-radius: 10px;
    padding: 6px 12px;
    color: {APP_TEXT};
}}
QPushButton:hover {{
    background-color: {BREEZE_BUTTON_HOV};
}}
QPushButton:pressed {{
    background-color: #2c3035;
}}
QPushButton:disabled {{
    color: {APP_TEXT_DIM};
    background-color: #2a2e32;
    border-color: #383c42;
}}
QPushButton:checked {{
    background-color: rgba(224, 169, 15, 0.16);
    border-color: rgba(224, 169, 15, 0.45);
    color: {BLITZ_300};
}}

/* Eingaben & Auswahl */
QComboBox, QLineEdit, QSpinBox, QPlainTextEdit, QTextEdit {{
    background-color: {BREEZE_VIEW};
    border: 1px solid {BREEZE_LINE};
    border-radius: 10px;
    padding: 6px 10px;
    selection-background-color: {BREEZE_BLUE};
}}
QComboBox:hover, QLineEdit:hover {{
    border-color: #4b515a;
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {BREEZE_BLUE};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {BREEZE_VIEW};
    border: 1px solid {BREEZE_LINE};
    border-radius: 8px;
    selection-background-color: {BREEZE_BLUE};
    outline: none;
}}

/* Tabs (Einstellungen) */
QTabWidget::pane {{
    border: 1px solid {BREEZE_LINE};
    border-radius: 12px;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {APP_TEXT_DIM};
    padding: 7px 14px;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {APP_TEXT};
    border-bottom: 2px solid {BLITZ_500};
}}

QCheckBox {{
    background: transparent;
    spacing: 8px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #4b515a;
    border-radius: 5px;
    min-height: 28px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""


def apply_theme(app) -> None:
    """Wendet das Blitztext-Glass-Theme global auf die QApplication an."""
    app.setStyleSheet(APP_QSS)


def create_app_icon() -> QIcon:
    """Marken-App-Icon: Mikrofon (hell) + Blitz (amber) auf dunklem Grund.

    Bevorzugt das gelieferte SVG aus dem Design-System; faellt auf eine
    programmatische Variante zurueck, falls der SVG-Loader fehlt.
    """
    svg_path = ASSETS_DIR / "logo-mark-dark.svg"
    if svg_path.exists():
        icon = QIcon(str(svg_path))
        if not icon.isNull() and icon.availableSizes():
            return icon
    return _painted_app_icon()


def _painted_app_icon() -> QIcon:
    """Fallback-Icon im Code gezeichnet (Mikrofon + Blitz, Breeze-Dark)."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # dunkler abgerundeter Hintergrund
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(BREEZE_WINDOW)))
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)

    # Mikrofon (hell)
    mic = QColor("#fcfcfc")
    painter.setPen(QPen(mic, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(QBrush(mic))
    painter.drawRoundedRect(23, 14, 14, 22, 7, 7)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(17, 28, 30, 22, 200 * 16, 140 * 16)
    painter.drawLine(32, 47, 32, 54)
    painter.drawLine(25, 54, 39, 54)

    # Blitz (amber)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(BLITZ_500)))
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QPolygonF
    bolt = QPolygonF([
        QPointF(34, 13), QPointF(26, 25), QPointF(31, 25),
        QPointF(28, 34), QPointF(38, 22), QPointF(33, 22),
    ])
    painter.drawPolygon(bolt)
    painter.end()
    return QIcon(pixmap)
