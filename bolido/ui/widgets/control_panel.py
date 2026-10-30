"""
Sidebar Control Panel UI component: input paths, hardware selection, detection parameters, and triggers.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from bolido.config import DetectionConfig, DeviceConfig, DeviceType
from bolido.ui.assets import get_asset_path
from bolido.ui.icons import ICON_ARCHIVE, ICON_FOLDER, get_svg_icon


class _DummyStatusLabel:
    """Headless proxy to absorb status label setText calls without displaying duplicate text."""
    def setText(self, text: str):
        pass
    def setStyleSheet(self, style: str):
        pass
    def setWordWrap(self, wrap: bool):
        pass


class ControlPanelWidget(QFrame):
    """Sidebar configuration and command panel."""

    start_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    open_folder_requested = pyqtSignal()
    export_zip_requested = pyqtSignal()
    about_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(340)
        self._is_analyzing = False
        self.status_label = _DummyStatusLabel()
        self._init_ui()

    def _create_help_badge(self, tooltip_text: str) -> QLabel:
        badge = QLabel("?")
        badge.setCursor(Qt.CursorShape.PointingHandCursor)
        badge.setToolTip(tooltip_text)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(18, 18)
        badge.setStyleSheet("""
            QLabel {
                background-color: #222736;
                color: #94A3B8;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 700;
                border: 1px solid #333B52;
            }
            QLabel:hover {
                background-color: #2E364B;
                color: #38BDF8;
                border-color: #38BDF8;
            }
        """)
        return badge

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        # Compact logo in top-left header
        self.logo_lbl = QLabel()
        self.logo_lbl.setObjectName("HeaderLogo")
        logo_path = get_asset_path("icon_32.png")
        if not logo_path.exists():
            logo_path = get_asset_path("logo_raw.png")
        if logo_path.exists():
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                scaled_pix = pix.scaledToHeight(26, Qt.TransformationMode.SmoothTransformation)
                self.logo_lbl.setPixmap(scaled_pix)
                self.logo_lbl.setFixedSize(scaled_pix.width(), 26)
        header_row.addWidget(self.logo_lbl)

        header_lbl = QLabel("BOLIDO")
        header_lbl.setStyleSheet("font-size: 20px; font-weight: 800; color: #60A5FA; letter-spacing: 1.5px;")

        self.about_btn = QPushButton("ⓘ About")
        self.about_btn.setObjectName("AboutButton")
        self.about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.about_btn.setToolTip("About BOLIDO (О программе)")
        self.about_btn.setStyleSheet("""
            QPushButton#AboutButton {
                background-color: transparent;
                color: #94A3B8;
                border: 1px solid #232A3B;
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#AboutButton:hover {
                background-color: #1E2433;
                color: #38BDF8;
                border-color: #38BDF8;
            }
            QPushButton#AboutButton:pressed {
                background-color: #161A24;
            }
        """)
        self.about_btn.clicked.connect(self.about_requested.emit)

        header_row.addWidget(header_lbl)
        header_row.addStretch()
        header_row.addWidget(self.about_btn)

        layout.addLayout(header_row)

        sub_lbl = QLabel("Offline Meteor Detection & Analysis")
        sub_lbl.setStyleSheet("font-size: 11px; color: #64748B; margin-bottom: 2px;")
        layout.addWidget(sub_lbl)

        # --------------------------------------------------------------------
        # 1. Source Group
        # --------------------------------------------------------------------
        src_group = QGroupBox("INPUT SOURCE")
        src_layout = QVBoxLayout(src_group)
        src_layout.setContentsMargins(12, 14, 12, 12)
        src_layout.setSpacing(8)

        radio_row = QHBoxLayout()
        self.radio_file = QRadioButton("Single Video")
        self.radio_file.setChecked(True)
        self.radio_folder = QRadioButton("Folder Batch")
        radio_row.addWidget(self.radio_file)
        radio_row.addWidget(self.radio_folder)
        src_layout.addLayout(radio_row)

        path_row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select video file or directory...")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_path)
        path_row.addWidget(self.path_input, stretch=1)
        path_row.addWidget(self.browse_btn)
        src_layout.addLayout(path_row)

        layout.addWidget(src_group)

        # --------------------------------------------------------------------
        # 2. Hardware Acceleration Group
        # --------------------------------------------------------------------
        hw_group = QGroupBox("HARDWARE ACCELERATION")
        hw_layout = QVBoxLayout(hw_group)
        hw_layout.setContentsMargins(12, 14, 12, 12)
        hw_layout.setSpacing(8)

        # Device selector
        dev_row = QHBoxLayout()
        dev_lbl = QLabel("Compute Device:")
        self.device_combo = QComboBox()
        self.device_combo.addItem("Auto (Recommended)", DeviceType.AUTO)
        self.device_combo.addItem("NVIDIA CUDA (GPU)", DeviceType.CUDA)
        self.device_combo.addItem("CPU (Multi-threaded)", DeviceType.CPU)

        dev_badge = self._create_help_badge(
            "Auto detects NVIDIA CUDA GPU for matrix screening.\n"
            "If CUDA is unavailable, seamlessly uses all CPU cores."
        )
        dev_row.addWidget(dev_lbl)
        dev_row.addWidget(dev_badge)
        dev_row.addStretch(1)
        dev_row.addWidget(self.device_combo)
        hw_layout.addLayout(dev_row)

        # Downscale pass
        down_row = QHBoxLayout()
        down_lbl = QLabel("Detection Pass:")
        self.downscale_combo = QComboBox()
        self.downscale_combo.addItem("1280px (Fast, Recommended)", 1280)
        self.downscale_combo.addItem("960px (Ultra Fast)", 960)
        self.downscale_combo.addItem("Native (Full Resolution)", 0)

        down_badge = self._create_help_badge(
            "Performs initial screening on downscaled frames to maximize FPS.\n"
            "Final clips and images are ALWAYS extracted in full native resolution."
        )
        down_row.addWidget(down_lbl)
        down_row.addWidget(down_badge)
        down_row.addStretch(1)
        down_row.addWidget(self.downscale_combo)
        hw_layout.addLayout(down_row)

        layout.addWidget(hw_group)

        # --------------------------------------------------------------------
        # 3. Detection Parameters Group
        # --------------------------------------------------------------------
        param_group = QGroupBox("DETECTION PARAMETERS")
        param_layout = QVBoxLayout(param_group)
        param_layout.setContentsMargins(12, 14, 12, 12)
        param_layout.setSpacing(8)

        # Sensitivity
        row_t = QHBoxLayout()
        lbl_t = QLabel("Sensitivity:")
        badge_t = self._create_help_badge("Pixel brightness difference above background.\nLower = more sensitive (25-50).")
        self.val_thresh = QLabel("35")
        self.val_thresh.setStyleSheet("color: #60A5FA; font-weight: 700; min-width: 28px;")
        row_t.addWidget(lbl_t)
        row_t.addWidget(badge_t)
        row_t.addStretch(1)
        row_t.addWidget(self.val_thresh)
        param_layout.addLayout(row_t)

        self.slider_thresh = QSlider(Qt.Orientation.Horizontal)
        self.slider_thresh.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider_thresh.setRange(10, 80)
        self.slider_thresh.setValue(35)
        self.slider_thresh.valueChanged.connect(lambda v: self.val_thresh.setText(str(v)))
        param_layout.addWidget(self.slider_thresh)

        # Min track length
        row_l = QHBoxLayout()
        lbl_l = QLabel("Min Track Length:")
        badge_l = self._create_help_badge("Minimum required trajectory length in pixels.\nRejects single-frame noise glitches.")
        self.val_len = QLabel("15 px")
        self.val_len.setStyleSheet("color: #60A5FA; font-weight: 700; min-width: 38px;")
        row_l.addWidget(lbl_l)
        row_l.addWidget(badge_l)
        row_l.addStretch(1)
        row_l.addWidget(self.val_len)
        param_layout.addLayout(row_l)

        self.slider_len = QSlider(Qt.Orientation.Horizontal)
        self.slider_len.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider_len.setRange(5, 60)
        self.slider_len.setValue(15)
        self.slider_len.valueChanged.connect(lambda v: self.val_len.setText(f"{v} px"))
        param_layout.addWidget(self.slider_len)

        # Buffer sec
        row_b = QHBoxLayout()
        lbl_b = QLabel("Clip Buffer:")
        badge_b = self._create_help_badge("Seconds retained before and after meteor in exported MP4 clips.")
        self.val_buf = QLabel("1.5 s")
        self.val_buf.setStyleSheet("color: #60A5FA; font-weight: 700; min-width: 38px;")
        row_b.addWidget(lbl_b)
        row_b.addWidget(badge_b)
        row_b.addStretch(1)
        row_b.addWidget(self.val_buf)
        param_layout.addLayout(row_b)

        self.slider_buf = QSlider(Qt.Orientation.Horizontal)
        self.slider_buf.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider_buf.setRange(5, 40)
        self.slider_buf.setValue(15)
        self.slider_buf.valueChanged.connect(lambda v: self.val_buf.setText(f"{v/10.0:.1f} s"))
        param_layout.addWidget(self.slider_buf)

        layout.addWidget(param_group)

        # --------------------------------------------------------------------
        # 4. Action Button (Single Start / Stop Toggle)
        # --------------------------------------------------------------------
        self.start_btn = QPushButton("▶  START ANALYSIS")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.clicked.connect(self._on_action_clicked)
        layout.addWidget(self.start_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        layout.addStretch(1)

        # Export Tools
        export_row = QHBoxLayout()
        export_row.setSpacing(8)

        self.open_folder_btn = QPushButton("  Open Folder")
        self.open_folder_btn.setIcon(get_svg_icon(ICON_FOLDER, size=15))
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self.open_folder_requested.emit)

        self.export_zip_btn = QPushButton("  Export ZIP")
        self.export_zip_btn.setIcon(get_svg_icon(ICON_ARCHIVE, size=15))
        self.export_zip_btn.setEnabled(False)
        self.export_zip_btn.clicked.connect(self.export_zip_requested.emit)

        export_row.addWidget(self.open_folder_btn)
        export_row.addWidget(self.export_zip_btn)
        layout.addLayout(export_row)

    def _on_action_clicked(self):
        if self._is_analyzing:
            self.cancel_requested.emit()
        else:
            self.start_requested.emit()

    def set_analyzing(self, analyzing: bool):
        """Switches single action button between Start Analysis and Stop Analysis modes."""
        self._is_analyzing = analyzing
        if analyzing:
            self.start_btn.setText("⏹  STOP ANALYSIS")
            self.start_btn.setObjectName("DangerButton")
        else:
            self.start_btn.setText("▶  START ANALYSIS")
            self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.setEnabled(True)
        self.start_btn.style().unpolish(self.start_btn)
        self.start_btn.style().polish(self.start_btn)

    def _browse_path(self):
        if self.radio_folder.isChecked():
            folder = QFileDialog.getExistingDirectory(self, "Select Video Folder")
            if folder:
                self.path_input.setText(folder)
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Video File",
                "",
                "Video Files (*.mp4 *.mkv *.avi *.mov *.m4v);;All Files (*)",
            )
            if file_path:
                self.path_input.setText(file_path)

    def build_config(self) -> DetectionConfig:
        dev_type = self.device_combo.currentData()
        target_w = self.downscale_combo.currentData()
        dev_config = DeviceConfig(
            device_type=dev_type,
            target_width=target_w,
            batch_size=8,
        )
        return DetectionConfig(
            threshold=float(self.slider_thresh.value()),
            min_length=float(self.slider_len.value()),
            buffer_sec=float(self.slider_buf.value()) / 10.0,
            learning_rate=0.05,
            save_clean=True,
            device=dev_config,
        )
