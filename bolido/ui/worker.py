"""
Background worker thread executing video analysis decoupled from Qt UI event loop.
Communicates strictly via typed Qt Signals, streaming detected events in real-time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import cv2
from PyQt6.QtCore import QThread, pyqtSignal

from bolido.config import DetectionConfig
from bolido.core.detector import MeteorDetector
from bolido.core.models import MeteorEvent


@dataclass
class VideoAnalysisResult:
    """Metadata package for a completed video detection run."""
    video_path: Path
    video_name: str
    video_duration_sec: float
    analysis_time_sec: float
    output_dir: Path
    xlsx_path: Optional[Path]
    csv_path: Optional[Path]
    events: List[MeteorEvent]
    master_raw_path: Optional[Path] = None
    master_annotated_path: Optional[Path] = None
    device_name: str = ""


class AnalysisWorker(QThread):
    """
    QThread worker orchestrating MeteorDetector on single or batch video inputs.
    Emits typed Qt signals to update UI without freezing the main application loop,
    streaming meteor events on-the-fly as soon as they are encoded.
    """

    # Typed Qt signals
    progress_signal = pyqtSignal(int, int, float, float)  # (cur_frame, total_frames, fps, speed_mult)
    status_signal = pyqtSignal(str)
    device_signal = pyqtSignal(str)  # Active compute device identifier
    event_detected_signal = pyqtSignal(object)  # Emits MeteorEvent as soon as clip/merge is encoded on-the-fly
    video_completed_signal = pyqtSignal(object)  # VideoAnalysisResult
    all_completed_signal = pyqtSignal(list, float, float)  # (results, total_vid_dur, total_elapsed)
    error_signal = pyqtSignal(str)

    def __init__(
        self,
        video_paths: List[Path],
        output_dir: Path,
        config: DetectionConfig,
    ):
        super().__init__()
        self.video_paths = video_paths
        self.output_dir = output_dir
        self.config = config
        self._is_cancelled = False

    def cancel(self) -> None:
        """Flags cancellation request to interrupt processing gracefully."""
        self._is_cancelled = True

    def run(self) -> None:
        """Main thread execution routine."""
        try:
            detector = MeteorDetector(config=self.config)

            results: List[VideoAnalysisResult] = []
            total_video_duration = 0.0
            t_all_start = time.time()

            for idx, video_path in enumerate(self.video_paths, start=1):
                if self._is_cancelled:
                    self.status_signal.emit("Analysis cancelled by user.")
                    break

                self.status_signal.emit(f"Analyzing {video_path.name} ({idx}/{len(self.video_paths)})...")

                cap = cv2.VideoCapture(str(video_path))
                fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()
                vid_dur = total_frames / fps if total_frames > 0 else 0.0
                total_video_duration += vid_dur

                t_start = time.time()

                def progress_cb(cur_f: int, tot_f: int, cur_fps: float, speed_mult: float):
                    self.progress_signal.emit(cur_f, tot_f, cur_fps, speed_mult)

                def cancel_check() -> bool:
                    return self._is_cancelled

                def on_event_exported(event: MeteorEvent):
                    # Immediately notify GUI to display event card in real time
                    self.event_detected_signal.emit(event)

                events = detector.process_video(
                    video_path=video_path,
                    output_dir=self.output_dir,
                    progress_callback=progress_cb,
                    cancel_check=cancel_check,
                    event_callback=on_event_exported,
                )

                elapsed = time.time() - t_start
                vid_out_dir = self.output_dir / f"{video_path.stem}_analysis"
                xlsx_path = vid_out_dir / "detections.xlsx"
                csv_path = vid_out_dir / "detections.csv"
                composites_dir = vid_out_dir / "composites"
                master_raw_file = composites_dir / "master_composite_raw.jpg"
                master_annotated_file = composites_dir / "master_composite_annotated.jpg"

                # Emit active device name
                active_device = detector.active_device_name or "CPU"
                self.device_signal.emit(active_device)

                res = VideoAnalysisResult(
                    video_path=video_path,
                    video_name=video_path.name,
                    video_duration_sec=vid_dur,
                    analysis_time_sec=elapsed,
                    output_dir=vid_out_dir,
                    xlsx_path=xlsx_path if xlsx_path.exists() else None,
                    csv_path=csv_path if csv_path.exists() else None,
                    events=events,
                    master_raw_path=master_raw_file if master_raw_file.exists() else None,
                    master_annotated_path=master_annotated_file if master_annotated_file.exists() else None,
                    device_name=active_device,
                )
                results.append(res)
                self.video_completed_signal.emit(res)

            total_elapsed = max(0.001, time.time() - t_all_start)
            self.all_completed_signal.emit(results, total_video_duration, total_elapsed)

        except Exception as e:
            self.error_signal.emit(str(e))
