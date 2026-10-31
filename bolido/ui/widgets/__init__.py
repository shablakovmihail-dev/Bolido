"""
UI Widgets package for Bolido.
"""

from bolido.ui.widgets.about_dialog import AboutDialog
from bolido.ui.widgets.control_panel import ControlPanelWidget
from bolido.ui.widgets.detections_gallery import DetectionsGalleryWidget
from bolido.ui.widgets.event_card import EventCardWidget
from bolido.ui.widgets.metric_card import MetricCardWidget
from bolido.ui.widgets.player import VideoPlayerWidget
from bolido.ui.widgets.splash import BolidoSplashScreen

__all__ = [
    "AboutDialog",
    "BolidoSplashScreen",
    "DetectionsGalleryWidget",
    "MetricCardWidget",
    "VideoPlayerWidget",
    "EventCardWidget",
    "ControlPanelWidget",
]
