"""
Monochrome vector icon registry and SVG renderer for Bolido UI.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

# ----------------------------------------------------------------------------
# SVG Definitions (clean geometric vector icons)
# ----------------------------------------------------------------------------

ICON_PLAY = """<svg viewBox="0 0 24 24" fill="currentColor">
<polygon points="8,5 20,12 8,19"/>
</svg>"""

ICON_PAUSE = """<svg viewBox="0 0 24 24" fill="currentColor">
<rect x="6" y="5" width="4" height="14" rx="1"/>
<rect x="14" y="5" width="4" height="14" rx="1"/>
</svg>"""

ICON_STEP_PREV = """<svg viewBox="0 0 24 24" fill="currentColor">
<rect x="5" y="5" width="2.5" height="14" rx="0.8"/>
<polygon points="19,19 8.5,12 19,5"/>
</svg>"""

ICON_STEP_NEXT = """<svg viewBox="0 0 24 24" fill="currentColor">
<polygon points="5,5 15.5,12 5,19"/>
<rect x="16.5" y="5" width="2.5" height="14" rx="0.8"/>
</svg>"""

ICON_LOOP = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
<polyline points="17 1 21 5 17 9"/>
<path d="M3 11V9a4 4 0 0 1 4-4h14"/>
<polyline points="7 23 3 19 7 15"/>
<path d="M21 13v2a4 4 0 0 1-4 4H3"/>
</svg>"""

ICON_TAB_VIDEO = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<rect x="2" y="4" width="20" height="16" rx="2"/>
<polygon points="10 8 16 12 10 16 10 8" fill="currentColor" stroke="none"/>
</svg>"""

ICON_TAB_MERGE = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
</svg>"""

ICON_TAB_SESSION = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<circle cx="12" cy="12" r="3" fill="currentColor"/>
<path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
</svg>"""

ICON_TAB_TABLE = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<line x1="8" y1="6" x2="21" y2="6"/>
<line x1="8" y1="12" x2="21" y2="12"/>
<line x1="8" y1="18" x2="21" y2="18"/>
<line x1="3" y1="6" x2="3.01" y2="6"/>
<line x1="3" y1="12" x2="3.01" y2="12"/>
<line x1="3" y1="18" x2="3.01" y2="18"/>
</svg>"""

ICON_FOLDER = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
</svg>"""

ICON_ARCHIVE = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<polyline points="21 8 21 21 3 21 3 8"/>
<rect x="1" y="3" width="22" height="5"/>
<line x1="10" y1="12" x2="14" y2="12"/>
</svg>"""


def get_svg_icon(
    svg_data: str,
    size: int = 16,
    normal_color: str = "#64748B",
    active_color: str = "#38BDF8",
    selected_color: str = "#F1F5F9",
) -> QIcon:
    """Builds a QIcon with distinct normal, active/hover, and selected pixmap states."""
    icon = QIcon()

    modes = [
        (QIcon.Mode.Normal, normal_color),
        (QIcon.Mode.Active, active_color),
        (QIcon.Mode.Selected, selected_color),
    ]

    for mode, color in modes:
        xml = svg_data.replace("currentColor", color).encode("utf-8")
        renderer = QSvgRenderer(xml)
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap, mode)

    return icon
