"""
Bolido Splash Screen - Modern Dark Minimal Startup Screen.
Displays initialization stages, hardware detection status, and smoothly fades into MainWindow.
"""

from __future__ import annotations

import time

try:
    from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt
    from PyQt6.QtGui import QColor, QFont, QGuiApplication, QPixmap
    from PyQt6.QtWidgets import (
        QApplication,
        QFrame,
        QHBoxLayout,
        QLabel,
        QProgressBar,
        QSplashScreen,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt  # type: ignore
    from PySide6.QtGui import QColor, QFont, QGuiApplication, QPixmap  # type: ignore
    from PySide6.QtWidgets import (  # type: ignore
        QApplication,
        QFrame,
        QHBoxLayout,
        QLabel,
        QProgressBar,
        QSplashScreen,
        QVBoxLayout,
        QWidget,
    )

from bolido import __version__
from bolido.ui.assets import get_asset_path


class BolidoSplashScreen(QSplashScreen):
    """
    Modern frameless Splash Screen for Bolido.
    Shows initialization progress, subsystem statuses, and smooth meteor progress.
    """

    def __init__(self):
        super().__init__()

        # Window flags & translucency
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(540, 380)

        # Center on primary screen
        self._center_on_screen()

        # Build UI & styles
        self._init_ui()
        self._apply_styles()

        # Keep reference to active animation to prevent garbage collection
        self._fade_anim: QPropertyAnimation | None = None

    def _center_on_screen(self):
        """Centers splash screen squarely in the active primary monitor."""
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Outer card container with dark graphite background and rounded corners
        self.card = QFrame()
        self.card.setObjectName("SplashCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(36, 26, 36, 26)
        card_layout.setSpacing(0)

        # Top Bar: Version & Accent dot
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        dot_label = QLabel("☄")
        dot_label.setObjectName("CometIcon")
        top_bar.addWidget(dot_label)

        top_bar.addStretch()

        ver_badge = QLabel(f"v{__version__}")
        ver_badge.setObjectName("VersionBadge")
        top_bar.addWidget(ver_badge)

        card_layout.addLayout(top_bar)
        card_layout.addStretch(1)

        # --------------------------------------------------------------------
        # Central Branding (Raw Logo Centered, Standard Title & Subtitle)
        # --------------------------------------------------------------------
        center_layout = QVBoxLayout()
        center_layout.setSpacing(8)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo Raw Image centered above progress bar
        self.logo_img_lbl = QLabel()
        self.logo_img_lbl.setObjectName("SplashLogoImage")
        self.logo_img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_raw_path = get_asset_path("logo_raw.png")
        if logo_raw_path.exists():
            raw_pixmap = QPixmap(str(logo_raw_path))
            if not raw_pixmap.isNull():
                scaled_logo = raw_pixmap.scaled(
                    110, 110,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.logo_img_lbl.setPixmap(scaled_logo)
        center_layout.addWidget(self.logo_img_lbl)

        # Standard Title: BOLIDO
        logo_label = QLabel(
            '<span style="font-size: 30px; font-weight: 800; '
            'letter-spacing: 3px; color: #F8FAFC;">BOLIDO</span>'
        )
        logo_label.setObjectName("LogoLabel")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(logo_label)

        sub_label = QLabel("OFFLINE METEOR & FIREBALL DETECTOR")
        sub_label.setObjectName("SubtitleLabel")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(sub_label)

        card_layout.addLayout(center_layout)
        card_layout.addStretch(1)

        # --------------------------------------------------------------------
        # Bottom: Progress Bar & Dynamic Status
        # --------------------------------------------------------------------
        bottom_layout = QVBoxLayout()
        bottom_layout.setSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("SplashProgressBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        bottom_layout.addWidget(self.progress_bar)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("Initializing...")
        self.status_label.setObjectName("StatusLabel")
        status_row.addWidget(self.status_label)

        status_row.addStretch()

        self.percent_label = QLabel("0%")
        self.percent_label.setObjectName("PercentLabel")
        status_row.addWidget(self.percent_label)

        bottom_layout.addLayout(status_row)
        card_layout.addLayout(bottom_layout)

        root_layout.addWidget(self.card)

    def _apply_styles(self):
        self.setStyleSheet("""
            QFrame#SplashCard {
                background-color: #0D1117;
                border: 1px solid #232A3B;
                border-radius: 16px;
            }

            QLabel#CometIcon {
                color: #38BDF8;
                font-size: 16px;
            }

            QLabel#VersionBadge {
                background-color: #161F30;
                color: #38BDF8;
                border: 1px solid #23354F;
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }

            QLabel#SplashLogoImage {
                background: transparent;
            }

            QLabel#LogoLabel {
                background: transparent;
            }

            QLabel#SubtitleLabel {
                color: #64748B;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2.5px;
                background: transparent;
            }

            QProgressBar#SplashProgressBar {
                background-color: #1E2433;
                border: none;
                border-radius: 2px;
                height: 4px;
            }

            QProgressBar#SplashProgressBar::chunk {
                border-radius: 2px;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #1E3A5F,
                    stop: 0.65 #38BDF8,
                    stop: 1 #FFFFFF
                );
            }

            QLabel#StatusLabel {
                color: #94A3B8;
                font-size: 11px;
                font-weight: 500;
                background: transparent;
            }

            QLabel#PercentLabel {
                color: #64748B;
                font-size: 11px;
                font-weight: 600;
                background: transparent;
            }
        """)

    def set_stage(self, progress: int, message: str, delay: float = 0.0):
        """
        Updates progress bar value and status text, optionally pauses slightly,
        and flushes the Qt event queue to render updates immediately.
        """
        self.progress_bar.setValue(progress)
        self.percent_label.setText(f"{progress}%")
        self.status_label.setText(message)
        QApplication.processEvents()
        if delay > 0:
            time.sleep(delay)
            QApplication.processEvents()

    def fade_out(self, main_window: QWidget | None = None, duration_ms: int = 250):
        """
        Smoothly fades out splash opacity from 1.0 to 0.0, displays main_window,
        and finishes/closes the splash screen upon animation completion.
        """
        if main_window is not None:
            main_window.showMaximized()
            main_window.raise_()

        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(duration_ms)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        def _cleanup():
            if main_window is not None:
                self.finish(main_window)
            else:
                self.close()

        self._fade_anim.finished.connect(_cleanup)
        self._fade_anim.start()
