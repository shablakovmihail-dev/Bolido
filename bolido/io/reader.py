"""
Asynchronous multi-threaded video capture and frame pre-processing.
Decouples disk I/O / decoding from computation with queues, dynamic ring-buffering, and downscaling.
"""

from __future__ import annotations

import collections
import math
import os
import queue
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np


class ThreadedVideoCapture:
    """
    Decodes video frames in a dedicated background worker thread into a thread-safe Queue.
    Maintains a ring buffer of full-resolution raw frames for pristine event extraction,
    and supplies downscaled grayscale frames for accelerated detection passes.
    """

    def __init__(
        self,
        video_path: Union[str, Path],
        target_width: Optional[int] = 1280,
        queue_size: int = 128,
        ring_buffer_size: Optional[int] = None,
        buffer_sec: Optional[float] = 1.5,
        max_expected_meteor_duration: int = 25,
    ):
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        self.queue_size = queue_size
        self._target_width = target_width

        # Probe video stream properties
        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video file: {self.video_path}")

        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0 or math.isnan(self.fps):
            self.fps = 30.0

        self.orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        # Dynamic ring buffer calculation based on UI buffer setting
        if buffer_sec is not None:
            self.buffer_frames = int(round(self.fps * float(buffer_sec)))
            # Ring buffer must hold pre-buffer + meteor duration + post-buffer + safety margin
            needed_ring_size = 2 * self.buffer_frames + max_expected_meteor_duration + 32
            self.ring_buffer_size = ring_buffer_size if ring_buffer_size is not None else max(120, needed_ring_size)
        else:
            self.buffer_frames = int(round(self.fps * 1.5))
            self.ring_buffer_size = ring_buffer_size or 300

        # Compute detection pass dimensions (downscaled if width > target_width)
        if self._target_width and self._target_width > 0 and self.orig_width > self._target_width:
            self.proc_width = int(self._target_width)
            scale = self.proc_width / float(self.orig_width)
            self.proc_height = int(round(self.orig_height * scale))
        else:
            self.proc_width = self.orig_width
            self.proc_height = self.orig_height

        self.scale_x = float(self.orig_width) / float(self.proc_width)
        self.scale_y = float(self.orig_height) / float(self.proc_height)

        # Threading and Queues
        self._queue: queue.Queue = queue.Queue(maxsize=self.queue_size)
        self._ring_buffer: collections.deque = collections.deque(maxlen=self.ring_buffer_size)
        self._ring_dict: Dict[int, np.ndarray] = {}
        self._ring_lock = threading.Lock()

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._started = False

    def start(self) -> ThreadedVideoCapture:
        """Starts decoding thread."""
        if self._started:
            return self
        self._started = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True, name="BolidoVideoReader")
        self._thread.start()
        return self

    def _worker(self) -> None:
        """Worker loop decoding frames asynchronously."""
        cap = cv2.VideoCapture(str(self.video_path))
        frame_idx = 0

        needs_downscale = (self.proc_width != self.orig_width or self.proc_height != self.orig_height)

        try:
            while not self._stop_event.is_set():
                ret, frame_orig = cap.read()
                if not ret:
                    break

                # Store raw full-resolution frame in ring buffer for pristine on-the-fly extraction
                with self._ring_lock:
                    if len(self._ring_buffer) >= self.ring_buffer_size:
                        old_idx = self._ring_buffer.popleft()
                        self._ring_dict.pop(old_idx, None)
                    self._ring_buffer.append(frame_idx)
                    self._ring_dict[frame_idx] = frame_orig

                # Prepare lightweight downscaled grayscale frame for fast screening
                if needs_downscale:
                    frame_down = cv2.resize(
                        frame_orig,
                        (self.proc_width, self.proc_height),
                        interpolation=cv2.INTER_AREA,
                    )
                else:
                    frame_down = frame_orig

                frame_gray = cv2.cvtColor(frame_down, cv2.COLOR_BGR2GRAY)

                # Blocking put into queue with periodic check for stop event
                while not self._stop_event.is_set():
                    try:
                        self._queue.put((frame_idx, frame_gray, frame_down), timeout=0.1)
                        break
                    except queue.Full:
                        continue

                frame_idx += 1

        finally:
            cap.release()
            # Push sentinel to signal EOF
            try:
                self._queue.put(None, timeout=0.5)
            except Exception:
                pass

    def read(self, timeout: float = 2.0) -> Optional[Tuple[int, np.ndarray, np.ndarray]]:
        """
        Retrieves next processed frame (frame_idx, frame_gray, frame_bgr).
        Returns None at end-of-stream or on timeout.
        """
        if not self._started:
            self.start()

        try:
            item = self._queue.get(timeout=timeout)
            if item is None:
                # Re-put sentinel for subsequent callers
                self._queue.put(None)
                return None
            return item
        except queue.Empty:
            return None

    def read_batch(
        self,
        batch_size: int,
        timeout: float = 1.0,
    ) -> List[Tuple[int, np.ndarray, np.ndarray]]:
        """Reads a batch of up to batch_size frames."""
        batch = []
        for _ in range(batch_size):
            item = self.read(timeout=timeout)
            if item is None:
                break
            batch.append(item)
        return batch

    def get_raw_frame(self, frame_idx: int) -> Optional[np.ndarray]:
        """
        Returns a single frame in native resolution from the ring buffer.
        If evicted from the ring buffer, seeks and retrieves directly from video.
        """
        with self._ring_lock:
            if frame_idx in self._ring_dict:
                return self._ring_dict[frame_idx].copy()

        cap = cv2.VideoCapture(str(self.video_path))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        cap.release()
        return frame if ret else None

    def get_raw_frames(self, start_frame: int, end_frame: int) -> List[np.ndarray]:
        """
        Extracts a sequence of frames in full native resolution for clip and composite generation.
        Fetches directly from RAM ring buffer without disk seek whenever available.
        """
        frames: List[np.ndarray] = []
        missing_indices: List[int] = []

        with self._ring_lock:
            for idx in range(start_frame, end_frame + 1):
                if idx in self._ring_dict:
                    frames.append(self._ring_dict[idx].copy())
                else:
                    frames.append(None)
                    missing_indices.append(idx)

        # Fallback disk seek only for frames that were already evicted from ring buffer
        if missing_indices:
            cap = cv2.VideoCapture(str(self.video_path))
            for miss_idx in missing_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, miss_idx)
                ret, frame = cap.read()
                if ret:
                    local_pos = miss_idx - start_frame
                    frames[local_pos] = frame
            cap.release()

        # Filter any None frames just in case
        return [f for f in frames if f is not None]

    def compute_base_canvas(self, num_samples: int = 30) -> np.ndarray:
        """
        Calculates a pristine static starry sky base canvas via median aggregation
        over initial frames in full native resolution to prevent star trails.
        """
        sample_frames = []
        cap = cv2.VideoCapture(str(self.video_path))
        num_to_read = min(num_samples * 2, max(1, self.total_frames))

        for i in range(num_to_read):
            ret, frame = cap.read()
            if not ret:
                break
            if i % 2 == 0 and len(sample_frames) < num_samples:
                sample_frames.append(frame)

        cap.release()

        if sample_frames:
            return np.median(sample_frames, axis=0).astype(np.uint8)
        return np.zeros((self.orig_height, self.orig_width, 3), dtype=np.uint8)

    def stop(self) -> None:
        """Stops reading thread and releases resources."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        with self._ring_lock:
            self._ring_dict.clear()
            self._ring_buffer.clear()
        # Drain queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Exception:
                break

    def __enter__(self) -> ThreadedVideoCapture:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
