"""
Metric Card UI Component for displaying real-time statistics and hardware indicators.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout


class MetricCardWidget(QFrame):
    """Refined astro HUD metric card."""

    def __init__(self, title: str, default_value: str = "—", accent_color: str = "#60A5FA", parent=None):
        super().__init__(parent)
        self.setObjectName("CardPanel")
        self.setStyleSheet("""
            QFrame#CardPanel {
                background-color: #161A24;
                border: 1px solid #232A3B;
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel(title.upper())
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #64748B; font-size: 10px; font-weight: 700; letter-spacing: 0.8px;")

        self.value_label = QLabel(default_value)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setStyleSheet(f"color: {accent_color}; font-size: 16px; font-weight: 700;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str, color: str = None) -> None:
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: 700;")
