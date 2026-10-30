"""
Bolido Desktop Main Window - PyQt6 Graphical User Interface.
"""

from __future__ import annotations

import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

import cv2
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QPoint, QRect, QSize, Qt, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QIcon, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from bolido.config import DetectionConfig, DeviceConfig, DeviceType
from bolido.core.backends.base import DeviceManager
from bolido.core.models import MeteorEvent
from bolido.ui.assets import get_asset_path
from bolido.ui.icons import (
    ICON_TAB_MERGE,
    ICON_TAB_SESSION,
    ICON_TAB_TABLE,
    ICON_TAB_VIDEO,
    get_svg_icon,
)
from bolido.ui.styles import GRAPHITE_INDIGO_THEME
from bolido.ui.widgets.about_dialog import AboutDialog
from bolido.ui.widgets.control_panel import ControlPanelWidget
from bolido.ui.widgets.event_card import EventCardWidget
from bolido.ui.widgets.metric_card import MetricCardWidget
from bolido.ui.widgets.player import VideoPlayerWidget
from bolido.ui.worker import AnalysisWorker, VideoAnalysisResult


def collect_video_files(input_path: Path) -> List[Path]:
    """Resolves input path into a list of supported video files."""
    valid_exts = {".mp4", ".mkv", ".avi", ".mov", ".m4v"}
    if input_path.is_file():
        if input_path.suffix.lower() in valid_exts:
            return [input_path]
        return []
    if input_path.is_dir():
        files = [p for p in input_path.iterdir() if p.is_file() and p.suffix.lower() in valid_exts]
        files.sort()
        return files
    return []


class BolidoMainWindow(QMainWindow):
    """Main Application Window for BOLIDO Meteor Detector."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BOLIDO — Offline Meteor & Fireball Detector")
        self.setMinimumSize(1180, 760)
        self.resize(1360, 860)

        # Set Window and Taskbar Icon
        icon_path = get_asset_path("app_icon.ico")
        if not icon_path.exists():
            icon_path = Path("assets/app_icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.current_events: List[MeteorEvent] = []
        self.selected_event: Optional[MeteorEvent] = None
        self.worker: Optional[AnalysisWorker] = None
        self.active_output_dir: Optional[Path] = None
        self.master_raw_path: Optional[Path] = None
        self.master_annotated_path: Optional[Path] = None
        self.show_clean_merge = False
        self._current_max_merge_pixmap: Optional[QPixmap] = None

        self.setAcceptDrops(True)
        QApplication.setStyle("Fusion")
        self._init_ui()
        self._apply_stylesheet()
        self._init_device_indicator()

        demo_video = Path("test_night_sky.mp4")
        if demo_video.exists():
            self.control_panel.path_input.setText(str(demo_video.resolve()))

    def _apply_stylesheet(self):
        self.setStyleSheet(GRAPHITE_INDIGO_THEME)

    def _init_device_indicator(self):
        dev_type, dev_name = DeviceManager.get_device_info()
        color = "#10B981" if dev_type == DeviceType.CUDA else "#38BDF8"
        self.card_device.set_value(dev_name, color)
        self.statusBar().showMessage(f"Ready  •  Device: {dev_name}")

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(14)

        # --------------------------------------------------------------------
        # Left Panel: Sidebar / Controls
        # --------------------------------------------------------------------
        self.control_panel = ControlPanelWidget()
        self.control_panel.start_requested.connect(self._on_start_analysis)
        self.control_panel.cancel_requested.connect(self._on_cancel_analysis)
        self.control_panel.open_folder_requested.connect(self._on_open_folder)
        self.control_panel.export_zip_requested.connect(self._on_export_zip)
        self.control_panel.about_requested.connect(self._on_open_about)
        main_layout.addWidget(self.control_panel)

        # --------------------------------------------------------------------
        # Right Area: Metrics Bar + Workspace
        # --------------------------------------------------------------------
        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)

        # 1. Top Metrics Bar (HUD Cards)
        metrics_bar = QHBoxLayout()
        metrics_bar.setSpacing(10)

        self.card_events = MetricCardWidget("METEORS DETECTED", "0", "#60A5FA")
        self.card_dur = MetricCardWidget("FOOTAGE DURATION", "0.0 s", "#94A3B8")
        self.card_proc_time = MetricCardWidget("ANALYSIS TIME", "0.0 s", "#94A3B8")
        self.card_speed = MetricCardWidget("PROCESSING SPEED", "—", "#34D399")
        self.card_device = MetricCardWidget("ACTIVE DEVICE", "Auto", "#38BDF8")

        metrics_bar.addWidget(self.card_events)
        metrics_bar.addWidget(self.card_dur)
        metrics_bar.addWidget(self.card_proc_time)
        metrics_bar.addWidget(self.card_speed)
        metrics_bar.addWidget(self.card_device)
        right_panel.addLayout(metrics_bar)

        # 2. Main Content Splitter: Gallery (Left) & Inspector (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)

        # Left Gallery Container
        gallery_container = QFrame()
        gallery_container.setObjectName("CardPanel")
        gallery_container.setFixedWidth(330)
        gallery_layout = QVBoxLayout(gallery_container)
        gallery_layout.setContentsMargins(10, 10, 10, 10)
        gallery_layout.setSpacing(8)

        gallery_header = QHBoxLayout()
        gallery_title = QLabel("DETECTIONS GALLERY")
        gallery_title.setStyleSheet("font-weight: 700; color: #94A3B8; font-size: 11px; letter-spacing: 0.6px;")
        self.count_badge = QLabel("0 events")
        self.count_badge.setStyleSheet("color: #60A5FA; font-weight: 700; font-size: 11px;")
        gallery_header.addWidget(gallery_title)
        gallery_header.addStretch(1)
        gallery_header.addWidget(self.count_badge)
        gallery_layout.addLayout(gallery_header)

        # Scroll Area for Event Cards
        self.gallery_scroll = QScrollArea()
        self.gallery_scroll.setWidgetResizable(True)
        self.gallery_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.gallery_content = QWidget()
        self.gallery_cards_layout = QVBoxLayout(self.gallery_content)
        self.gallery_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.gallery_cards_layout.setSpacing(8)
        self.gallery_cards_layout.addStretch(1)
        self.gallery_scroll.setWidget(self.gallery_content)
        gallery_layout.addWidget(self.gallery_scroll)

        splitter.addWidget(gallery_container)

        # Right Inspector Tabs
        self.inspector_tabs = QTabWidget()
        self.inspector_tabs.setDocumentMode(False)

        # Tab 1: Video Player
        self.player_widget = VideoPlayerWidget()
        self.inspector_tabs.addTab(self.player_widget, get_svg_icon(ICON_TAB_VIDEO, size=16), "VIDEO CLIP")

        # Tab 2: Max-Pixel Merge
        self.merge_tab = self._create_merge_tab()
        self.inspector_tabs.addTab(self.merge_tab, get_svg_icon(ICON_TAB_MERGE, size=16), "MAX-PIXEL MERGE")

        # Tab 3: Session Composite
        self.session_tab = self._create_session_tab()
        self.inspector_tabs.addTab(self.session_tab, get_svg_icon(ICON_TAB_SESSION, size=16), "SESSION COMPOSITE")

        # Tab 4: Detections Table
        self.table_tab = self._create_table_tab()
        self.inspector_tabs.addTab(self.table_tab, get_svg_icon(ICON_TAB_TABLE, size=16), "DETECTIONS TABLE")

        splitter.addWidget(self.inspector_tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        right_panel.addWidget(splitter, stretch=1)
        main_layout.addLayout(right_panel, stretch=1)

    def _create_merge_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Controls bar
        bar = QHBoxLayout()
        self.merge_mode_toggle = QPushButton("Switch to Clean Image")
        self.merge_mode_toggle.clicked.connect(self._toggle_clean_annotated)

        self.save_merge_btn = QPushButton("Save Image As...")
        self.save_merge_btn.clicked.connect(self._save_active_merge)

        bar.addWidget(self.merge_mode_toggle)
        bar.addStretch(1)
        bar.addWidget(self.save_merge_btn)
        layout.addLayout(bar)

        # Image view
        self.merge_scroll = QScrollArea()
        self.merge_scroll.setWidgetResizable(True)
        self.merge_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.merge_scroll.setStyleSheet("background-color: #0E1117; border: 1px solid #2B3244; border-radius: 8px;")

        self.merge_label = QLabel("Select an event from the gallery to view the Max-Pixel Merge composite.")
        self.merge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.merge_label.setStyleSheet("color: #64748B; font-size: 13px;")
        self.merge_scroll.setWidget(self.merge_label)
        layout.addWidget(self.merge_scroll, stretch=1)

        return widget

    def _create_session_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        bar = QHBoxLayout()
        self.session_mode_toggle = QPushButton("Show Raw Session Composite")
        self.session_mode_toggle.clicked.connect(self._toggle_session_mode)

        self.save_session_btn = QPushButton("Save Session Image...")
        self.save_session_btn.clicked.connect(self._save_session_composite)

        bar.addWidget(self.session_mode_toggle)
        bar.addStretch(1)
        bar.addWidget(self.save_session_btn)
        layout.addLayout(bar)

        self.session_scroll = QScrollArea()
        self.session_scroll.setWidgetResizable(True)
        self.session_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.session_scroll.setStyleSheet("background-color: #0E1117; border: 1px solid #2B3244; border-radius: 8px;")

        self.session_label = QLabel("Session Master Composite will appear here after video processing completes.")
        self.session_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.session_label.setStyleSheet("color: #64748B; font-size: 13px;")
        self.session_scroll.setWidget(self.session_label)
        layout.addWidget(self.session_scroll, stretch=1)

        self._show_raw_session = False
        return widget

    def _create_table_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Time (sec)",
            "Duration",
            "Track Length",
            "Peak Intensity",
            "Clip Path",
            "Composite Path",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemClicked.connect(self._on_table_item_clicked)
        self.table.currentCellChanged.connect(self._on_table_cell_changed)
        self.table.itemDoubleClicked.connect(self._on_table_item_double_clicked)
        layout.addWidget(self.table)

        return widget

    # ------------------------------------------------------------------------
    # Execution Logic
    # ------------------------------------------------------------------------

    def _on_start_analysis(self):
        in_path_str = self.control_panel.path_input.text().strip()
        if not in_path_str:
            QMessageBox.warning(self, "Missing Path", "Please select an input video file or folder.")
            return

        in_path = Path(in_path_str)
        if not in_path.exists():
            QMessageBox.warning(self, "Path Not Found", f"Specified path does not exist:\n{in_path_str}")
            return

        video_files = collect_video_files(in_path)
        if not video_files:
            QMessageBox.warning(self, "No Videos", "No supported video files (.mp4, .mkv, .avi) found.")
            return

        out_root = Path("./output")
        out_root.mkdir(parents=True, exist_ok=True)
        self.active_output_dir = out_root

        # Reset UI
        self._clear_gallery()
        self.current_events.clear()
        self.table.setRowCount(0)
        self.selected_event = None
        self.card_events.set_value("0")
        self.card_dur.set_value("0.0 s")
        self.card_proc_time.set_value("...")
        self.card_speed.set_value("...", "#34D399")

        # Configure worker
        config = self.control_panel.build_config()

        # Update initial device indicator
        dev_type, dev_name = DeviceManager.get_device_info(config.device)
        color = "#10B981" if dev_type == DeviceType.CUDA else "#38BDF8"
        self.card_device.set_value(dev_name, color)

        self.control_panel.set_analyzing(True)
        self.control_panel.progress_bar.setValue(0)
        self.control_panel.status_label.setText("Starting analysis...")

        self.worker = AnalysisWorker(video_files, out_root, config)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.status_signal.connect(self._on_status)
        self.worker.device_signal.connect(self._on_device_reported)
        self.worker.event_detected_signal.connect(self._on_event_streamed)
        self.worker.video_completed_signal.connect(self._on_video_completed)
        self.worker.all_completed_signal.connect(self._on_all_completed)
        self.worker.error_signal.connect(self._on_error)
        self.worker.start()

    def _on_cancel_analysis(self):
        if self.worker and self.worker.isRunning():
            self.control_panel.status_label.setText("Cancelling...")
            self.worker.cancel()

    @pyqtSlot(int, int, float, float)
    def _on_progress(self, cur_frame: int, tot_frames: int, cur_fps: float, speed_mult: float):
        if tot_frames > 0:
            pct = int((cur_frame / tot_frames) * 100)
            self.control_panel.progress_bar.setValue(pct)
            self.control_panel.status_label.setText(
                f"Frame {cur_frame}/{tot_frames} ({pct}%) • {cur_fps:.0f} FPS ({speed_mult:.1f}x)"
            )
            self.card_speed.set_value(f"{cur_fps:.0f} FPS ({speed_mult:.1f}x)", "#34D399")

    @pyqtSlot(str)
    def _on_status(self, text: str):
        self.control_panel.status_label.setText(text)
        self.statusBar().showMessage(text)

    @pyqtSlot(str)
    def _on_device_reported(self, device_name: str):
        color = "#10B981" if "CUDA" in device_name else "#38BDF8"
        self.card_device.set_value(device_name, color)
        self.statusBar().showMessage(f"Device: {device_name}")

    @pyqtSlot(object)
    def _on_event_streamed(self, event: MeteorEvent):
        """Streaming slot: displays detected meteor card on-the-fly without waiting for video EOF."""
        # Avoid duplicate entries if already added
        if any(e.event_id == event.event_id for e in self.current_events):
            return

        self.current_events.append(event)

        card = EventCardWidget(event)
        card.clicked.connect(self._on_event_card_selected)
        self.gallery_cards_layout.insertWidget(self.gallery_cards_layout.count() - 1, card)

        self.count_badge.setText(f"{len(self.current_events)} events")
        self.card_events.set_value(str(len(self.current_events)))
        self._append_table_row(event)

        # Autoselect the first detected event immediately for preview
        if len(self.current_events) == 1:
            self._select_event(event)

    @pyqtSlot(object)
    def _on_video_completed(self, result: VideoAnalysisResult):
        self.master_raw_path = result.master_raw_path
        self.master_annotated_path = result.master_annotated_path
        self._load_session_composite()

        # Ensure all events are displayed in gallery and table
        for ev in result.events:
            if not any(e.event_id == ev.event_id for e in self.current_events):
                self.current_events.append(ev)
                card = EventCardWidget(ev)
                card.clicked.connect(self._on_event_card_selected)
                self.gallery_cards_layout.insertWidget(self.gallery_cards_layout.count() - 1, card)
                self._append_table_row(ev)

        self.count_badge.setText(f"{len(self.current_events)} events")
        self.card_events.set_value(str(len(self.current_events)))

        if result.events and not self.selected_event:
            self._select_event(result.events[0])

    @pyqtSlot(list, float, float)
    def _on_all_completed(self, results: List[VideoAnalysisResult], total_video_dur: float, total_elapsed: float):
        self.control_panel.set_analyzing(False)
        self.control_panel.progress_bar.setValue(100)
        self.control_panel.open_folder_btn.setEnabled(True)
        self.control_panel.export_zip_btn.setEnabled(True)

        self.card_dur.set_value(f"{total_video_dur:.1f} s")
        self.card_proc_time.set_value(f"{total_elapsed:.1f} s")

        if total_elapsed > 0 and total_video_dur > 0:
            speed_mult = total_video_dur / total_elapsed
            total_frames = int(total_video_dur * 30.0)
            avg_fps = total_frames / total_elapsed
            self.card_speed.set_value(f"{avg_fps:.0f} FPS ({speed_mult:.1f}x)", "#34D399")

        total_meteors = sum(len(r.events) for r in results)
        if total_meteors > 0:
            self.control_panel.status_label.setText(f"Completed! {total_meteors} meteors detected.")
        else:
            self.control_panel.status_label.setText("Completed: No meteors detected in footage.")

    @pyqtSlot(str)
    def _on_error(self, err: str):
        self.control_panel.set_analyzing(False)
        self.control_panel.status_label.setText("Error during processing.")
        QMessageBox.critical(self, "Processing Error", f"An error occurred:\n{err}")

    @pyqtSlot()
    def _on_open_about(self):
        """Displays the modal About Bolido dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    # ------------------------------------------------------------------------
    # Gallery & Inspector Interactions
    # ------------------------------------------------------------------------

    def _clear_gallery(self):
        while self.gallery_cards_layout.count() > 1:
            item = self.gallery_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.count_badge.setText("0 events")

    def _on_event_card_selected(self, event: MeteorEvent):
        self._select_event(event)

    def _select_event(self, event: MeteorEvent, sync_table: bool = True):
        self.selected_event = event

        for i in range(self.gallery_cards_layout.count() - 1):
            widget = self.gallery_cards_layout.itemAt(i).widget()
            if isinstance(widget, EventCardWidget):
                is_selected = (widget.event.event_id == event.event_id)
                widget.set_selected(is_selected)
                if is_selected:
                    self.gallery_scroll.ensureWidgetVisible(widget)

        # Sync table selection (Gallery -> Table)
        if sync_table:
            row_idx = next(
                (i for i, ev in enumerate(self.current_events) if ev.event_id == event.event_id),
                -1,
            )
            if row_idx >= 0 and self.table.rowCount() > row_idx:
                self.table.blockSignals(True)
                self.table.selectRow(row_idx)
                self.table.blockSignals(False)

        # 1. Load video clip in player
        if event.clip_path and Path(event.clip_path).exists():
            self.player_widget.load_video(event.clip_path, autoplay=True)

        # 2. Render max merge
        self._render_active_max_merge()

    def _render_active_max_merge(self):
        if not self.selected_event:
            return
        path_to_load = (
            self.selected_event.clean_merge_path
            if self.show_clean_merge
            else self.selected_event.max_merge_path
        )
        if not path_to_load and self.selected_event.max_merge_path:
            path_to_load = self.selected_event.max_merge_path

        if path_to_load and Path(path_to_load).exists():
            pix = QPixmap(str(Path(path_to_load).resolve()))
            self._current_max_merge_pixmap = pix
            scaled = pix.scaled(
                self.merge_scroll.size() - QSize(20, 20),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.merge_label.setPixmap(scaled)
        else:
            self.merge_label.setText("No Max-Merge image available for this event.")

    def _toggle_clean_annotated(self):
        self.show_clean_merge = not self.show_clean_merge
        self.merge_mode_toggle.setText(
            "Switch to Annotated Image" if self.show_clean_merge else "Switch to Clean Image"
        )
        self._render_active_max_merge()

    def _save_active_merge(self):
        if not self.selected_event:
            return
        src = self.selected_event.clean_merge_path if self.show_clean_merge else self.selected_event.max_merge_path
        if not src or not Path(src).exists():
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Save Image", Path(src).name, "Images (*.jpg *.png)")
        if dest:
            shutil.copy2(src, dest)
            QMessageBox.information(self, "Saved", f"Image saved to:\n{dest}")

    def _load_session_composite(self):
        src = self.master_raw_path if self._show_raw_session else self.master_annotated_path
        if src and Path(src).exists():
            pix = QPixmap(str(Path(src).resolve()))
            scaled = pix.scaled(
                self.session_scroll.size() - QSize(20, 20),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.session_label.setPixmap(scaled)

    def _toggle_session_mode(self):
        self._show_raw_session = not self._show_raw_session
        self.session_mode_toggle.setText(
            "Show Annotated Session Composite" if self._show_raw_session else "Show Raw Session Composite"
        )
        self._load_session_composite()

    def _save_session_composite(self):
        src = self.master_raw_path if self._show_raw_session else self.master_annotated_path
        if not src or not Path(src).exists():
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Save Session Image", Path(src).name, "Images (*.jpg *.png)")
        if dest:
            shutil.copy2(src, dest)
            QMessageBox.information(self, "Saved", f"Session image saved to:\n{dest}")

    def _append_table_row(self, ev: MeteorEvent):
        row = self.table.rowCount()
        self.table.insertRow(row)

        start_m, start_s = int(ev.start_time_sec // 60), ev.start_time_sec % 60
        dur_sec = ev.duration_frames / 30.0

        items = [
            f"#{ev.event_id:03d}",
            f"{start_m:02d}:{start_s:05.2f}",
            f"{dur_sec:.2f}s ({ev.duration_frames} f)",
            f"{ev.approx_length_px:.1f} px",
            f"{ev.peak_intensity:.1f}",
            Path(ev.clip_path).name if ev.clip_path else "",
            Path(ev.max_merge_path).name if ev.max_merge_path else "",
        ]
        for col, text in enumerate(items):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, col, item)

    def _select_event_by_index(self, row: int, sync_table: bool = True):
        if 0 <= row < len(self.current_events):
            self._select_event(self.current_events[row], sync_table=sync_table)

    def _on_table_item_clicked(self, item: QTableWidgetItem):
        self._select_event_by_index(item.row(), sync_table=False)

    def _on_table_cell_changed(self, cur_row: int, cur_col: int, prev_row: int, prev_col: int):
        if cur_row >= 0 and cur_row != prev_row:
            self._select_event_by_index(cur_row, sync_table=False)

    def _on_table_item_double_clicked(self, item: QTableWidgetItem):
        self._select_event_by_index(item.row(), sync_table=False)
        self.inspector_tabs.setCurrentIndex(0)

    def _on_open_folder(self):
        if self.active_output_dir and self.active_output_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.active_output_dir.resolve())))

    def _on_export_zip(self):
        if not self.active_output_dir or not self.active_output_dir.exists():
            return
        dest_zip, _ = QFileDialog.getSaveFileName(self, "Export Session ZIP Archive", "bolido_session.zip", "ZIP Archives (*.zip)")
        if not dest_zip:
            return

        with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(self.active_output_dir):
                for f in files:
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(self.active_output_dir)
                    zf.write(full_p, rel_p)

        QMessageBox.information(self, "Export Complete", f"Successfully exported full session archive to:\n{dest_zip}")

    # ------------------------------------------------------------------------
    # Drag and Drop
    # ------------------------------------------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            first_path = Path(urls[0].toLocalFile())
            if first_path.is_dir():
                self.control_panel.radio_folder.setChecked(True)
                self.control_panel.path_input.setText(str(first_path.resolve()))
            elif first_path.is_file():
                self.control_panel.radio_file.setChecked(True)
                self.control_panel.path_input.setText(str(first_path.resolve()))
