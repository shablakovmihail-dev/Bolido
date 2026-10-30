"""
Event Card UI component displaying thumbnail, timings, intensity, and metadata for a detected meteor.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from bolido.core.models import MeteorEvent


class EventCardWidget(QFrame):
    """Gallery card item representing a detected meteor."""

    clicked = pyqtSignal(object)

    def __init__(self, event: MeteorEvent, parent=None):
        super().__init__(parent)
        self.event = event
        self.setObjectName("CardPanel")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_selected = False
        self._init_ui()
        self._update_style()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Thumbnail (R=6px)
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(90, 60)
        self.thumb_label.setStyleSheet("background-color: #0E1117; border-radius: 6px; border: 1px solid #232A3B;")
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._load_thumbnail()
        layout.addWidget(self.thumb_label)

        # Details
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Title row
        title_row = QHBoxLayout()
        self.title_lbl = QLabel(f"EVENT #{self.event.event_id:03d}")
        self.title_lbl.setStyleSheet("font-weight: 700; color: #60A5FA; font-size: 13px;")

        start_m, start_s = int(self.event.start_time_sec // 60), self.event.start_time_sec % 60
        self.time_lbl = QLabel(f"{start_m:02d}:{start_s:04.1f}s")
        self.time_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")

        title_row.addWidget(self.title_lbl)
        title_row.addStretch(1)
        title_row.addWidget(self.time_lbl)
        info_layout.addLayout(title_row)

        # Metrics row
        dur_sec = self.event.duration_frames / 30.0
        metrics_text = (
            f"Frames: <b style='color:#E2E8F0;'>{self.event.duration_frames}</b> ({dur_sec:.2f}s)  •  "
            f"Len: <b style='color:#E2E8F0;'>{self.event.approx_length_px:.0f}px</b>"
        )
        self.metrics_lbl = QLabel(metrics_text)
        self.metrics_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        info_layout.addWidget(self.metrics_lbl)

        # Peak intensity
        self.intensity_lbl = QLabel(f"Peak Intensity: <b style='color:#F59E0B;'>{self.event.peak_intensity:.0f}</b>")
        self.intensity_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        info_layout.addWidget(self.intensity_lbl)

        layout.addLayout(info_layout, stretch=1)

    def _load_thumbnail(self):
        thumb_path = self.event.clean_merge_path or self.event.max_merge_path
        if thumb_path and Path(thumb_path).exists():
            pix = QPixmap(str(Path(thumb_path).resolve()))
            if not pix.isNull():
                self.thumb_label.setPixmap(
                    pix.scaled(
                        self.thumb_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return
        self.thumb_label.setText("No Preview")

    def set_selected(self, selected: bool):
        self._is_selected = selected
        self._update_style()

    def _update_style(self):
        if self._is_selected:
            self.setStyleSheet("""
                QFrame#CardPanel {
                    background-color: #1E293B;
                    border: 1px solid #3B82F6;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#CardPanel {
                    background-color: #161A24;
                    border: 1px solid #232A3B;
                    border-radius: 8px;
                }
                QFrame#CardPanel:hover {
                    background-color: #1A202E;
                    border-color: #3B82F6;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.event)
        super().mousePressEvent(event)
