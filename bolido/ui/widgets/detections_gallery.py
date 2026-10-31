"""
Detections Gallery UI component for Bolido.
Monolithic container without redundant inner borders.
"""

from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from bolido.core.models import MeteorEvent
from bolido.ui.widgets.event_card import EventCardWidget


class DetectionsGalleryWidget(QFrame):
    """Gallery container displaying detected meteor event cards."""

    event_selected = pyqtSignal(object)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("CardPanel")
        self.setFixedWidth(330)
        self.cards: List[EventCardWidget] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header Row
        header_layout = QHBoxLayout()
        title_lbl = QLabel("DETECTIONS GALLERY")
        title_lbl.setStyleSheet("font-weight: 700; color: #94A3B8; font-size: 11px; letter-spacing: 0.6px;")

        self.count_badge = QLabel("0 events")
        self.count_badge.setStyleSheet("""
            background-color: #1E293B;
            color: #60A5FA;
            font-size: 11px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 6px;
            border: 1px solid #2B3A55;
        """)
        header_layout.addWidget(title_lbl)
        header_layout.addStretch(1)
        header_layout.addWidget(self.count_badge)
        layout.addLayout(header_layout)

        # Scrollable gallery container with zero nested borders
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("gallery_scroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setLineWidth(0)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.gallery_content = QWidget()
        self.gallery_content.setStyleSheet("background: transparent; border: none;")
        self.cards_layout = QVBoxLayout(self.gallery_content)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch(1)

        self.scroll_area.setWidget(self.gallery_content)
        layout.addWidget(self.scroll_area)

    def add_event(self, event: MeteorEvent) -> EventCardWidget:
        card = EventCardWidget(event)
        card.clicked.connect(self.event_selected.emit)
        self.cards.append(card)
        self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        self.count_badge.setText(f"{len(self.cards)} events")
        return card

    def clear(self):
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()
        self.count_badge.setText("0 events")
