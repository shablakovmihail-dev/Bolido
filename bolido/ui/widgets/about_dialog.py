"""
About Dialog for Bolido application.
Displays program metadata, description, tech stack, and links in the dark astro aesthetic.
"""

from __future__ import annotations

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont, QIcon, QPixmap
    from PyQt6.QtWidgets import (
        QDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    from PySide6.QtCore import Qt  # type: ignore
    from PySide6.QtGui import QFont, QIcon, QPixmap  # type: ignore
    from PySide6.QtWidgets import (  # type: ignore
        QDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

from bolido import __version__
from bolido.ui.assets import get_asset_path


class AboutDialog(QDialog):
    """Modal About dialog for BOLIDO."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("About BOLIDO")
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.setModal(True)
        self.setFixedSize(520, 500)

        # Set dialog window icon
        icon_path = get_asset_path("app_icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._init_ui()
        self._apply_styles()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 22, 24, 20)
        main_layout.setSpacing(14)

        # --------------------------------------------------------------------
        # 1. Header / Logo Section
        # --------------------------------------------------------------------
        header_row = QHBoxLayout()
        header_row.setSpacing(14)
        header_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Logo Pixmap (icon_64 or logo_raw scaled smoothly)
        logo_icon_lbl = QLabel()
        logo_icon_lbl.setObjectName("AboutLogoImage")
        logo_file = get_asset_path("icon_64.png")
        if not logo_file.exists():
            logo_file = get_asset_path("logo_raw.png")
        if logo_file.exists():
            pix = QPixmap(str(logo_file))
            if not pix.isNull():
                scaled_pix = pix.scaled(
                    48, 48,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                logo_icon_lbl.setPixmap(scaled_pix)
                logo_icon_lbl.setFixedSize(48, 48)
        header_row.addWidget(logo_icon_lbl)

        # Text column in header
        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        title_badge_row = QHBoxLayout()
        title_badge_row.setSpacing(8)

        logo_label = QLabel("BOLIDO")
        logo_label.setObjectName("LogoLabel")
        title_badge_row.addWidget(logo_label)

        version_badge = QLabel(f"Version {__version__}")
        version_badge.setObjectName("VersionBadge")
        title_badge_row.addWidget(version_badge)
        title_badge_row.addStretch()

        text_col.addLayout(title_badge_row)

        subtitle_label = QLabel("Offline Meteor & Fireball Detector")
        subtitle_label.setObjectName("SubtitleLabel")
        text_col.addWidget(subtitle_label)

        header_row.addLayout(text_col)
        main_layout.addLayout(header_row)

        # --------------------------------------------------------------------
        # 2. Description Box
        # --------------------------------------------------------------------
        desc_box = QFrame()
        desc_box.setObjectName("DescriptionCard")
        desc_layout = QVBoxLayout(desc_box)
        desc_layout.setContentsMargins(14, 12, 14, 12)

        desc_text = QLabel(
            "Автономный инструмент компьютерного зрения для покадрового анализа "
            "ночных видеозаписей, таймлапсов и обзорных съёмок неба. "
            "Обнаруживает метеоры, болиды и кратковременные оптические транзиенты, "
            "фильтрует спутники и самолеты, собирает итоговые Max-Merge композиты "
            "сессии и нарезает видеоклипы событий."
        )
        desc_text.setObjectName("DescriptionText")
        desc_text.setWordWrap(True)
        desc_layout.addWidget(desc_text)

        main_layout.addWidget(desc_box)

        # --------------------------------------------------------------------
        # 3. Tech Stack Section
        # --------------------------------------------------------------------
        stack_box = QFrame()
        stack_box.setObjectName("StackCard")
        stack_layout = QVBoxLayout(stack_box)
        stack_layout.setContentsMargins(14, 12, 14, 12)
        stack_layout.setSpacing(8)

        stack_title = QLabel("TECH STACK")
        stack_title.setObjectName("SectionHeader")
        stack_layout.addWidget(stack_title)

        tech_specs = [
            ("Core & CV", "Python 3.10+, OpenCV, NumPy", "#60A5FA"),
            ("Acceleration", "Multi-threaded Ring Buffer, NVIDIA CUDA (Torch) / CPU", "#38BDF8"),
            ("UI / GUI", "PySide6 (Dark Minimal Astro-Theme)", "#A78BFA"),
            ("Export", "OpenPyXL, MP4 (H.264)", "#34D399"),
        ]

        for category, detail, dot_color in tech_specs:
            row = QHBoxLayout()
            row.setSpacing(8)

            dot = QLabel("●")
            dot.setStyleSheet(f"color: {dot_color}; font-size: 8px; margin-top: 1px;")

            cat_lbl = QLabel(category)
            cat_lbl.setObjectName("TechCategory")
            cat_lbl.setFixedWidth(82)

            val_lbl = QLabel(detail)
            val_lbl.setObjectName("TechDetail")

            row.addWidget(dot)
            row.addWidget(cat_lbl)
            row.addWidget(val_lbl, stretch=1)
            stack_layout.addLayout(row)

        main_layout.addWidget(stack_box)

        # --------------------------------------------------------------------
        # 4. Author & Repository Link
        # --------------------------------------------------------------------
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)

        github_label = QLabel(
            '<a href="https://github.com/bolido-astro/bolido" '
            'style="color: #38BDF8; text-decoration: none; font-weight: 600;">'
            'GitHub Repository ↗</a>'
        )
        github_label.setObjectName("GithubLink")
        github_label.setOpenExternalLinks(True)
        footer_layout.addWidget(github_label)

        footer_layout.addStretch()

        # --------------------------------------------------------------------
        # 5. Close Button
        # --------------------------------------------------------------------
        close_btn = QPushButton("Close")
        close_btn.setObjectName("CloseButton")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)

        main_layout.addLayout(footer_layout)

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #161A24;
                border: 1px solid #232A3B;
                border-radius: 12px;
            }

            QLabel#AboutLogoImage {
                background: transparent;
            }

            QLabel#LogoLabel {
                font-size: 24px;
                font-weight: 800;
                color: #60A5FA;
                letter-spacing: 2px;
            }

            QLabel#VersionBadge {
                background-color: #1E293B;
                color: #38BDF8;
                font-size: 11px;
                font-weight: 700;
                padding: 2px 7px;
                border-radius: 5px;
                border: 1px solid #2B3A55;
            }

            QLabel#SubtitleLabel {
                font-size: 12px;
                font-weight: 500;
                color: #94A3B8;
                letter-spacing: 0.3px;
                margin-bottom: 2px;
            }

            QFrame#DescriptionCard {
                background-color: #11141D;
                border: 1px solid #1E2433;
                border-radius: 8px;
            }

            QLabel#DescriptionText {
                color: #CBD5E1;
                font-size: 12px;
                line-height: 140%;
            }

            QFrame#StackCard {
                background-color: #11141D;
                border: 1px solid #1E2433;
                border-radius: 8px;
            }

            QLabel#SectionHeader {
                color: #64748B;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.8px;
            }

            QLabel#TechCategory {
                color: #94A3B8;
                font-size: 11px;
                font-weight: 600;
            }

            QLabel#TechDetail {
                color: #E2E8F0;
                font-size: 11px;
                font-weight: 400;
            }

            QLabel#GithubLink {
                font-size: 12px;
            }

            QLabel#GithubLink:hover {
                color: #60A5FA;
            }

            QPushButton#CloseButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border: 1px solid #3B82F6;
                border-radius: 8px;
                padding: 6px 20px;
                font-size: 12px;
                font-weight: 600;
                min-width: 80px;
            }

            QPushButton#CloseButton:hover {
                background-color: #1D4ED8;
                border-color: #60A5FA;
            }

            QPushButton#CloseButton:pressed {
                background-color: #1E40AF;
            }
        """)
