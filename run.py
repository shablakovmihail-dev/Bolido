#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOLIDO - Offline Meteor Detector & Night Sky Analyzer
Application Entry Point for Desktop GUI
"""

import sys
import time
from pathlib import Path

# Explicit AppUserModelID for Windows Taskbar icon display
if sys.platform == "win32":
    try:
        import ctypes
        app_id = "bolido.astro.detector.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

try:
    from PyQt6.QtCore import QEasingCurve, QPropertyAnimation
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication
except ImportError:
    from PySide6.QtCore import QEasingCurve, QPropertyAnimation  # type: ignore
    from PySide6.QtGui import QIcon  # type: ignore
    from PySide6.QtWidgets import QApplication  # type: ignore

from bolido.ui.widgets.splash import BolidoSplashScreen


def main():
    # Auto-generate icons if missing on first launch (development mode)
    if not getattr(sys, "frozen", False):
        try:
            from build_assets import ensure_assets
            ensure_assets()
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("BOLIDO")
    app.setOrganizationName("BOLIDO")

    # Set application & taskbar icon
    from bolido.ui.assets import get_asset_path
    icon_path = get_asset_path("app_icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # 1. Отображаем Splash Screen сразу при запуске
    splash = BolidoSplashScreen()
    splash.show()
    app.processEvents()

    # 2. Этапы инициализации подсистем
    splash.set_stage(15, "Loading configuration...", delay=0.08)
    from bolido.config import DetectionConfig, DeviceConfig  # noqa: F401

    splash.set_stage(40, "Checking hardware acceleration (CUDA / CPU)...", delay=0.1)
    from bolido.core.backends.base import DeviceManager
    _ = DeviceManager.get_device_info()

    splash.set_stage(70, "Initializing computer vision engine...", delay=0.1)
    from bolido.core.detector import MeteorDetector  # noqa: F401

    splash.set_stage(90, "Building dark UI components...", delay=0.08)
    from bolido.ui.app import BolidoMainWindow
    window = BolidoMainWindow()

    splash.set_stage(100, "Ready", delay=0.15)

    # 3. Плавное затухание заставки и бесшовный переход в главное окно
    splash.fade_out(main_window=window, duration_ms=250)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
