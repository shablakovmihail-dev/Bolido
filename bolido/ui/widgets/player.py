"""
Smooth OpenCV-driven video player widget with scrub slider, frame-step navigation, and playback controls.
"""

from pathlib import Path
from typing import Optional

import cv2
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QPoint, QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QImage, QKeyEvent, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStyle,
    QStyleOptionComboBox,
    QStylePainter,
    QVBoxLayout,
    QWidget,
)

from bolido.ui.icons import (
    ICON_LOOP,
    ICON_PAUSE,
    ICON_PLAY,
    ICON_STEP_NEXT,
    ICON_STEP_PREV,
    get_svg_icon,
)


class SpeedSelectorComboBox(QComboBox):
    """Refined speed selector combo box with optically centered label."""

    def paintEvent(self, event):
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        opt.currentText = ""  # Delegate label drawing to custom centered text
        painter = QStylePainter(self)
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt)
        painter.setPen(QColor("#E2E8F0"))
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.currentText())


class VideoPlayerWidget(QWidget):
    """Integrated OpenCV video player widget."""

    frame_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_path: Optional[str] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.total_frames = 0
        self.fps = 30.0
        self.current_frame = 0
        self.is_playing = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next_frame)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video Screen Frame (Seamlessly spans tab area, no redundant outer borders)
        self.screen_frame = QFrame()
        self.screen_frame.setStyleSheet("""
            QFrame {
                background-color: #0E1117;
                border: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 15px;
            }
        """)
        screen_layout = QVBoxLayout(self.screen_frame)
        screen_layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setText("No Video Loaded")
        self.video_label.setStyleSheet("color: #64748B; font-size: 14px; font-weight: 500;")
        screen_layout.addWidget(self.video_label)
        layout.addWidget(self.screen_frame, stretch=1)

        # Bottom Controls Panel (Transparent background preserving outer card rounded border)
        self.ctrl_frame = QFrame()
        self.ctrl_frame.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
                border-top: 1px solid #232A3B;
                border-bottom-left-radius: 15px;
                border-bottom-right-radius: 15px;
            }
        """)
        ctrl_layout = QVBoxLayout(self.ctrl_frame)
        ctrl_layout.setContentsMargins(12, 10, 12, 10)
        ctrl_layout.setSpacing(8)

        # Slider row (Time badge, Slider, Frame badge strictly centered)
        slider_row = QHBoxLayout()
        slider_row.setSpacing(10)

        self.time_lbl = QLabel("00:00.0 / 00:00.0")
        self.time_lbl.setFixedHeight(24)
        self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_lbl.setStyleSheet("""
            background-color: #1C2230;
            color: #94A3B8;
            font-size: 11px;
            font-family: monospace;
            font-weight: 600;
            padding: 2px 8px;
            border: 1px solid #283042;
            border-radius: 6px;
        """)

        self.scrub_slider = QSlider(Qt.Orientation.Horizontal)
        self.scrub_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scrub_slider.setRange(0, 0)
        self.scrub_slider.sliderMoved.connect(self._on_slider_moved)

        self.frame_lbl = QLabel("F: 0 / 0")
        self.frame_lbl.setFixedHeight(24)
        self.frame_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frame_lbl.setStyleSheet("""
            background-color: #1C2230;
            color: #94A3B8;
            font-size: 11px;
            font-family: monospace;
            font-weight: 600;
            padding: 2px 8px;
            border: 1px solid #283042;
            border-radius: 6px;
        """)

        slider_row.addWidget(self.time_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
        slider_row.addWidget(self.scrub_slider, stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)
        slider_row.addWidget(self.frame_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
        ctrl_layout.addLayout(slider_row)

        # Buttons row (Compact 32px height, baseline aligned)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        # Play / Pause (32x32)
        self.play_btn = QPushButton()
        self.play_btn.setObjectName("PlayerBtn")
        self.play_btn.setFixedSize(32, 32)
        self.play_btn.setToolTip("Play / Pause (Space)")
        self.play_btn.setIcon(get_svg_icon(ICON_PLAY, size=15))
        self.play_btn.clicked.connect(self.toggle_play)

        # Step Previous (32x32)
        self.prev_btn = QPushButton()
        self.prev_btn.setObjectName("PlayerBtn")
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.setToolTip("Previous Frame (Left Arrow)")
        self.prev_btn.setIcon(get_svg_icon(ICON_STEP_PREV, size=15))
        self.prev_btn.clicked.connect(lambda: self.step_frame(-1))

        # Step Next (32x32)
        self.next_btn = QPushButton()
        self.next_btn.setObjectName("PlayerBtn")
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.setToolTip("Next Frame (Right Arrow)")
        self.next_btn.setIcon(get_svg_icon(ICON_STEP_NEXT, size=15))
        self.next_btn.clicked.connect(lambda: self.step_frame(1))

        # Loop Toggle Button (32x32, checkable)
        self.loop_btn = QPushButton()
        self.loop_btn.setObjectName("PlayerBtn")
        self.loop_btn.setFixedSize(32, 32)
        self.loop_btn.setCheckable(True)
        self.loop_btn.setChecked(True)
        self.loop_btn.setToolTip("Loop Playback")
        self.loop_btn.setIcon(get_svg_icon(ICON_LOOP, size=15))

        # Unified Speed Selector (Single dropdown combo box, 32px height, centered text)
        self.speed_combo = SpeedSelectorComboBox()
        self.speed_combo.setObjectName("speedSelector")
        self.speed_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.speed_combo.setFixedHeight(32)
        self.speed_combo.setFixedWidth(92)
        self.speed_combo.setToolTip("Playback Speed")
        for s in ["0.25x", "0.5x", "1.0x", "1.5x", "2.0x"]:
            self.speed_combo.addItem(f"Speed: {s}", s)
        for i in range(self.speed_combo.count()):
            self.speed_combo.setItemData(i, Qt.AlignmentFlag.AlignCenter, Qt.ItemDataRole.TextAlignmentRole)
        self.speed_combo.setCurrentIndex(2)  # 1.0x
        self.speed_combo.currentTextChanged.connect(self._update_playback_speed)

        btn_row.addWidget(self.play_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        btn_row.addWidget(self.prev_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        btn_row.addWidget(self.next_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        btn_row.addWidget(self.loop_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        btn_row.addWidget(self.speed_combo, alignment=Qt.AlignmentFlag.AlignVCenter)
        btn_row.addStretch(1)

        ctrl_layout.addLayout(btn_row)
        layout.addWidget(self.ctrl_frame)

    @property
    def loop_chk(self):
        """Compatibility property for loop state."""
        return self.loop_btn

    def unload_video(self):
        """Explicitly releases media capture and frame buffers to prevent memory caching."""
        self.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.video_path = None
        self.total_frames = 0
        self.current_frame = 0
        self.video_label.clear()
        self.video_label.setText("No Video Loaded")
        import gc
        gc.collect()

    def setSource(self, url: QtCore.QUrl):
        """Compatibility method for media source lifecycle."""
        if not url or url.isEmpty():
            self.unload_video()
        else:
            local_path = url.toLocalFile() if url.isLocalFile() else url.toString()
            self.load_video(local_path)

    def load_video(self, video_path: str, autoplay: bool = True):
        self.unload_video()

        self.video_path = video_path
        p = Path(video_path)
        if not p.exists():
            self.video_label.setText(f"File not found:\n{p.name}")
            return

        self.cap = cv2.VideoCapture(str(p.resolve()), cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(str(p.resolve()))
        if not self.cap.isOpened():
            self.video_label.setText("Error loading video.")
            return

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        if self.fps <= 0:
            self.fps = 30.0

        self.scrub_slider.setRange(0, max(0, self.total_frames - 1))
        self.seek(0)

        if autoplay and self.total_frames > 0:
            self.play()

    def play(self):
        if not self.cap or not self.cap.isOpened() or self.total_frames <= 0:
            return
        self.is_playing = True
        self.play_btn.setIcon(get_svg_icon(ICON_PAUSE, size=15))
        self._update_playback_speed(self.speed_combo.currentText())

    def pause(self):
        self.is_playing = False
        self.play_btn.setIcon(get_svg_icon(ICON_PLAY, size=15))
        self._timer.stop()

    def toggle_play(self):
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def stop(self):
        self.pause()
        self.current_frame = 0

    def _update_playback_speed(self, text: str):
        if not self.is_playing:
            return
        speed_val = self.speed_combo.currentData()
        if speed_val:
            speed = float(str(speed_val).replace("x", ""))
        else:
            speed = float(text.replace("Speed:", "").replace("x", "").strip())
        interval_ms = int(1000.0 / (self.fps * speed))
        self._timer.start(max(10, interval_ms))

    def _next_frame(self):
        if not self.cap:
            return
        if self.current_frame + 1 >= self.total_frames:
            if self.loop_btn.isChecked():
                self.seek(0)
            else:
                self.pause()
            return

        self.seek(self.current_frame + 1)

    def step_frame(self, delta: int):
        self.pause()
        target = max(0, min(self.total_frames - 1, self.current_frame + delta))
        self.seek(target)

    def _on_slider_moved(self, pos: int):
        self.pause()
        self.seek(pos)

    def seek(self, frame_num: int):
        if not self.cap or not self.cap.isOpened():
            return
        self.current_frame = frame_num
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()
        if ret:
            self._render_frame(frame)
            del frame
            self.scrub_slider.blockSignals(True)
            self.scrub_slider.setValue(frame_num)
            self.scrub_slider.blockSignals(False)
            self._update_time_labels()
            self.frame_changed.emit(frame_num)

    def _render_frame(self, frame: cv2.Mat):
        target_size = self.screen_frame.size() - QSize(16, 16)
        tw = min(1280, max(10, target_size.width()))
        th = min(800, max(10, target_size.height()))

        h, w = frame.shape[:2]
        scale = min(tw / float(w), th / float(h), 1.0)
        disp_w = max(2, int(round(w * scale)))
        disp_h = max(2, int(round(h * scale)))

        # Downscale in OpenCV first so we allocate tiny ~0.5 MB buffer instead of 25.2 MB!
        if disp_w != w or disp_h != h:
            frame_disp = cv2.resize(frame, (disp_w, disp_h), interpolation=cv2.INTER_AREA)
        else:
            frame_disp = frame

        rgb = cv2.cvtColor(frame_disp, cv2.COLOR_BGR2RGB)
        dh, dw, dch = rgb.shape
        qimg = QImage(rgb.data, dw, dh, dch * dw, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        self.video_label.setPixmap(pix)
        del qimg
        del pix
        if frame_disp is not frame:
            del frame_disp
        del rgb

    def _update_time_labels(self):
        cur_sec = self.current_frame / self.fps if self.fps > 0 else 0
        tot_sec = self.total_frames / self.fps if self.fps > 0 else 0

        cur_m, cur_s = int(cur_sec // 60), cur_sec % 60
        tot_m, tot_s = int(tot_sec // 60), tot_sec % 60

        self.time_lbl.setText(f"{cur_m:02d}:{cur_s:04.1f} / {tot_m:02d}:{tot_s:04.1f}")
        self.frame_lbl.setText(f"F: {self.current_frame}/{self.total_frames}")

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space:
            self.toggle_play()
            event.accept()
        elif event.key() == Qt.Key.Key_Left:
            self.step_frame(-1)
            event.accept()
        elif event.key() == Qt.Key.Key_Right:
            self.step_frame(1)
            event.accept()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.cap and self.cap.isOpened() and not self.is_playing:
            self.seek(self.current_frame)

    def closeEvent(self, event):
        self.unload_video()
        super().closeEvent(event)
