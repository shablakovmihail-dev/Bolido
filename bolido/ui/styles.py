"""
Astro Dark Minimal (Graphite & Indigo) design tokens and palette stylesheet for Bolido Qt application.
"""

GRAPHITE_INDIGO_THEME = """
/* Global Window & Background */
QMainWindow, QDialog {
    background-color: #12151C;
}

QWidget {
    color: #E2E8F0;
    font-family: "Segoe UI", "SF Pro Display", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

/* Eliminate black rectangular backgrounds on text */
QLabel {
    background: transparent;
    background-color: transparent;
    color: #E2E8F0;
}

QRadioButton, QCheckBox {
    background: transparent;
    background-color: transparent;
    color: #94A3B8;
    outline: none;
}

QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #2B3244;
    background-color: #151822;
    outline: none;
}

QRadioButton::indicator {
    border-radius: 8px;
}

QRadioButton::indicator:checked, QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #3B82F6;
}

/* Sidebar & Panels (Outer Cards: R=16px) */
QFrame#Sidebar, QFrame#CardPanel {
    background-color: #161A24;
    border: 1px solid #232A3B;
    border-radius: 16px;
}

/* GroupBox Container with Integrated Titles */
QGroupBox {
    border: 1px solid #232A3B;
    border-radius: 14px;
    margin-top: 10px;
    padding-top: 14px;
    background-color: #161A24;
    font-weight: 700;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #718096;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    background-color: transparent;
}

/* Push Buttons (Nested Elements: R=8px, padding=8px 14px) */
QPushButton {
    background-color: #1E2433;
    color: #E2E8F0;
    border: 1px solid #2B3244;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 500;
    outline: none;
}

QPushButton:hover {
    background-color: #273044;
    border-color: #3B82F6;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #161A25;
}

QPushButton:disabled {
    background-color: #161922;
    border-color: #242938;
    color: #475569;
}

/* Primary Action: Slate-Indigo */
QPushButton#PrimaryButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #3B82F6;
    font-weight: 600;
    font-size: 13px;
    padding: 9px 16px;
    border-radius: 8px;
    outline: none;
}

QPushButton#PrimaryButton:hover {
    background-color: #1D4ED8;
    border-color: #60A5FA;
}

QPushButton#PrimaryButton:disabled {
    background-color: #1A2233;
    color: #475569;
    border: 1px solid #232A3B;
}

/* Danger / Stop Action: Muted Burgundy */
QPushButton#DangerButton {
    background-color: #7F1D1D;
    color: #FECACA;
    border: 1px solid #991B1B;
    font-weight: 600;
    font-size: 13px;
    padding: 9px 16px;
    border-radius: 8px;
    outline: none;
}

QPushButton#DangerButton:hover {
    background-color: #991B1B;
    color: #FFFFFF;
}

QPushButton#DangerButton:disabled {
    background-color: #1E2433;
    color: #64748B;
    border-color: #2B3244;
}

/* Compact Player Control Buttons (32x32px, R=8px) */
QPushButton#PlayerBtn {
    background-color: #1E2433;
    color: #E2E8F0;
    border: 1px solid #2B3244;
    border-radius: 8px;
    padding: 0px;
    width: 32px;
    height: 32px;
    min-width: 32px;
    min-height: 32px;
    max-width: 32px;
    max-height: 32px;
    outline: none;
}

QPushButton#PlayerBtn:hover {
    background-color: #273044;
    border-color: #38BDF8;
    color: #FFFFFF;
}

QPushButton#PlayerBtn:pressed {
    background-color: #161A25;
}

QPushButton#PlayerBtn:checked {
    background-color: #1D4ED8;
    border-color: #38BDF8;
    color: #FFFFFF;
}

/* Line Edit (Nested: R=8px) */
QLineEdit {
    background-color: #151822;
    border: 1px solid #2B3244;
    border-radius: 8px;
    padding: 6px 10px;
    color: #F8FAFC;
    outline: none;
}

QLineEdit:focus {
    border: 1px solid #3B82F6;
    background-color: #181C28;
    outline: none;
}

/* Sliders (Meteor Glow & Zero Focus Artifacts) */
QSlider, QSlider:focus, QSlider:active {
    background: transparent;
    background-color: transparent;
    border: none;
    outline: none;
}

QSlider:horizontal, QSlider:horizontal:focus, QSlider:horizontal:active {
    min-height: 24px;
    max-height: 24px;
    border: none;
    outline: none;
}

QSlider::groove:horizontal, QSlider::groove:horizontal:focus {
    border: none;
    height: 3px;
    background: #1E2433;
    border-radius: 1.5px;
    outline: none;
}

QSlider::sub-page:horizontal, QSlider::sub-page:horizontal:focus {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 rgba(14, 22, 38, 0.2),
        stop: 0.35 rgba(24, 50, 85, 0.5),
        stop: 0.75 rgba(45, 140, 225, 0.8),
        stop: 1.0 #38BDF8);
    height: 3px;
    border-radius: 1.5px;
    border: none;
    outline: none;
}

QSlider::add-page:horizontal, QSlider::add-page:horizontal:focus {
    border: none;
    height: 3px;
    background: #1E2433;
    border-radius: 1.5px;
    outline: none;
}

QSlider::handle:horizontal, QSlider::handle:horizontal:focus {
    background: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.5, fx: 0.5, fy: 0.5,
        stop: 0.0 #FFFFFF,
        stop: 0.35 #FFFFFF,
        stop: 0.70 #38BDF8,
        stop: 0.95 rgba(56, 189, 248, 0.75),
        stop: 1.0 rgba(56, 189, 248, 0.15));
    border: none;
    outline: none;
    width: 16px;
    height: 16px;
    margin: -6.5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.5, fx: 0.5, fy: 0.5,
        stop: 0.0 #FFFFFF,
        stop: 0.50 #FFFFFF,
        stop: 0.80 #7DD3FC,
        stop: 1.0 #38BDF8);
    border: none;
    outline: none;
    width: 18px;
    height: 18px;
    margin: -7.5px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:pressed {
    background: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.5, fx: 0.5, fy: 0.5,
        stop: 0.0 #FFFFFF,
        stop: 0.65 #FFFFFF,
        stop: 0.88 #BAE6FD,
        stop: 1.0 #67E8F9);
    border: none;
    outline: none;
    width: 18px;
    height: 18px;
    margin: -7.5px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:disabled {
    background: #334155;
    border: none;
    outline: none;
}

QSlider::sub-page:horizontal:disabled {
    background: #242C3D;
}

/* Combo Box (Nested: R=8px) */
QComboBox {
    background-color: #151822;
    border: 1px solid #2B3244;
    border-radius: 8px;
    padding: 6px 12px;
    color: #E2E8F0;
    outline: none;
}

QComboBox:hover {
    border-color: #3B82F6;
}

QComboBox:focus {
    border-color: #3B82F6;
    outline: none;
}

QComboBox::drop-down {
    border: none;
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #1C202C;
    border: 1px solid #2B3244;
    border-radius: 8px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
    color: #E2E8F0;
    outline: none;
}

/* Compact Speed Selector in Video Player (Symmetric padding, R=8px matching buttons) */
QComboBox#speedSelector {
    background-color: #1C2230;
    border: 1px solid #283042;
    border-radius: 8px;
    color: #E2E8F0;
    font-size: 11px;
    font-weight: 600;
    min-height: 24px;
    height: 32px;
    padding: 4px 10px;
    outline: none;
}

QComboBox#speedSelector:hover {
    border-color: #38BDF8;
    background-color: #242C3E;
}

QComboBox#speedSelector::drop-down {
    border: none;
    width: 0px;
}

QComboBox#speedSelector::down-arrow {
    image: none;
    width: 0px;
    height: 0px;
}

QComboBox#speedSelector QAbstractItemView {
    background-color: #1C202C;
    border: 1px solid #283042;
    border-radius: 8px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
    color: #E2E8F0;
    outline: none;
}

/* Scroll Bars */
QScrollBar:vertical {
    border: none;
    background: #12151C;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #2B3244;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #3B82F6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #12151C;
    height: 8px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #2B3244;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: #3B82F6;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Progress Bar */
QProgressBar {
    background-color: #161B26;
    border: none;
    border-radius: 4px;
    height: 8px;
    min-height: 8px;
    max-height: 8px;
    text-align: center;
    color: transparent;
    font-size: 0px;
}

QProgressBar::chunk {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #1E3A5F,
        stop: 0.85 #38BDF8,
        stop: 1.0 #FFFFFF);
    border-radius: 4px;
}

/* Detections Gallery Scroll Area (Seamless monolithic container, zero nested borders) */
QScrollArea#gallery_scroll,
QScrollArea#gallery_scroll > QWidget > QWidget {
    border: none;
    background: transparent;
    background-color: transparent;
}

/* Seamless Tab Widget (Selected Tab Melts into Pane: R=16px) */
QTabWidget::pane {
    border: 1px solid #232A3B;
    border-radius: 16px;
    border-top-left-radius: 0px;
    background-color: #161A24;
}

QTabWidget > QStackedWidget,
QTabWidget > QStackedWidget > QWidget {
    background: transparent;
    background-color: transparent;
}

QTabBar {
    qproperty-drawBase: 0;
    left: 0px;
    margin: 0px;
    margin-left: 0px;
    padding: 0px;
    padding-left: 0px;
    background: transparent;
    border: none;
}

QTabBar::scroller {
    width: 0px;
}

QTabBar QToolButton {
    width: 0px;
    height: 0px;
    padding: 0px;
    margin: 0px;
    border: none;
}

QTabBar::tab {
    background-color: #10131A;
    border: 1px solid #232A3B;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 6px 11px;
    margin-right: -4px;
    color: #64748B;
    font-weight: 600;
    font-size: 11px;
    outline: none;
}

QTabBar::tab:selected {
    background-color: #161A24;
    color: #F1F5F9;
    border: 1px solid #232A3B;
    border-bottom: 1px solid #161A24;
    margin-bottom: -1px;
    z-index: 10;
    outline: none;
}

QTabBar::tab:focus,
QTabBar::tab:selected:focus {
    outline: none;
    border-color: #232A3B;
}

QTabBar::tab:hover:!selected {
    color: #E2E8F0;
    background-color: #181E2B;
}

QTabBar::tab:first {
    margin-left: 0px;
    border-top-left-radius: 8px;
}

QTabBar::tab:last {
    margin-right: 0px;
}

/* Table Widget (R=12px) */
QTableWidget {
    background-color: #161A24;
    border: 1px solid #232A3B;
    gridline-color: #242A3A;
    color: #E2E8F0;
    border-radius: 12px;
    outline: none;
    selection-background-color: #1E293B;
    selection-color: #F8FAFC;
}

/* Modals & Dialogs (R=16px) */
QDialog, QMessageBox {
    background-color: #161A24;
    border: 1px solid #232A3B;
    border-radius: 16px;
}

QTableWidget::item:selected {
    background-color: #1E293B;
    color: #F8FAFC;
}

QHeaderView::section {
    background-color: #1C202C;
    color: #94A3B8;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #232A3B;
    border-right: 1px solid #242A3A;
    font-weight: 600;
    font-size: 11px;
}

/* Splitter */
QSplitter::handle {
    background-color: transparent;
}

QSplitter::handle:horizontal {
    width: 8px;
}

QSplitter::handle:vertical {
    height: 8px;
}
"""
