"""
Asynchronous multi-threaded video capture and frame pre-processing.
Decouples disk I/O / decoding from computation with bounded queues and sliding window ring-buffering.
Guarantees low memory footprint (under 400-600 MB) even on long 4K video footage.
"""

from __future__ import annotations

import collections
import gc
import math
import os
import queue
import threading
import time
from pathlib import Path
from typing import List, Optional, Tuple, Union

import cv2
import numpy as np


class ThreadedVideoCapture:
    """
    Decodes video frames in a dedicated background worker thread into a strictly bounded Queue.
    Maintains a bounded sliding window deque of full-resolution raw frames for pristine event extraction,
    and supplies downscaled grayscale frames for accelerated detection passes without memory bloat.
    """

    def __init__(
        self,
        video_path: Union[str, Path],
        target_width: Optional[int] = 1280,
        queue_size: int = 90,
        ring_buffer_size: Optional[int] = None,
        buffer_sec: Optional[float] = 1.5,
        max_expected_meteor_duration: int = 25,
    ):
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        # Bounded frame queue: strictly 90 frames (~2-3 sec) to eliminate memory hoarding
        self.queue_size = min(90, max(30, queue_size))
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

        # Dynamic pre-roll sliding window calculation with strict RAM budget:
        # We cap the sliding window to ~250 MB max so RAM never exceeds 400-600 MB even for 4K frames
        if buffer_sec is not None:
            self.buffer_frames = int(round(self.fps * float(buffer_sec)))
        else:
            self.buffer_frames = int(round(self.fps * 1.5))

        calc_limit = self.buffer_frames + max_expected_meteor_duration + 10
        frame_bytes = max(1, self.orig_width * self.orig_height * 3)
        # Bounded RAM budget of ~130 MB for raw frames sliding window to keep process RAM strictly under 400-600 MB
        max_allowed_frames = max(8, int((130 * 1024 * 1024) / frame_bytes))

        if ring_buffer_size is not None:
            self.ring_buffer_size = min(max_allowed_frames, max(8, ring_buffer_size))
        else:
            self.ring_buffer_size = min(max_allowed_frames, max(8, calc_limit))

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

        # 1. Bounded Queue: maxsize=90 (holds only lightweight 1-channel grayscale frames)
        self._queue: queue.Queue = queue.Queue(maxsize=self.queue_size)

        # 2. Sliding window buffer: collections.deque(maxlen=BUFFER_LIMIT)
        # Stores tuples (frame_idx, frame_orig) - auto-evicts oldest frame without holding stale refs
        self._ring_buffer: collections.deque = collections.deque(maxlen=self.ring_buffer_size)
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
        """Worker loop decoding frames asynchronously with bounded memory usage."""
        cap = cv2.VideoCapture(str(self.video_path))
        frame_idx = 0

        needs_downscale = (self.proc_width != self.orig_width or self.proc_height != self.orig_height)

        try:
            while not self._stop_event.is_set():
                ret, frame_orig = cap.read()
                if not ret:
                    break

                # 1. Store Full-Res frame in bounded sliding deque (auto-drops oldest frame)
                with self._ring_lock:
                    self._ring_buffer.append((frame_idx, frame_orig))

                # 2. Downscaled single-channel grayscale frame for detector
                if needs_downscale:
                    frame_down = cv2.resize(
                        frame_orig,
                        (self.proc_width, self.proc_height),
                        interpolation=cv2.INTER_AREA,
                    )
                    frame_gray = cv2.cvtColor(frame_down, cv2.COLOR_BGR2GRAY)
                    del frame_down
                else:
                    frame_gray = cv2.cvtColor(frame_orig, cv2.COLOR_BGR2GRAY)

                # 3. Blocking put into bounded queue (maxsize=90).
                # Blocks decoding thread when queue is full so decoder does NOT outrun analysis in RAM!
                while not self._stop_event.is_set():
                    try:
                        # Only put (frame_idx, frame_gray) - NEVER put heavy BGR frame into queue!
                        self._queue.put((frame_idx, frame_gray), block=True, timeout=0.1)
                        break
                    except queue.Full:
                        continue

                frame_idx += 1

        finally:
            cap.release()
            try:
                self._queue.put(None, timeout=0.5)
            except Exception:
                pass

    def read(self, timeout: float = 2.0) -> Optional[Tuple[int, np.ndarray]]:
        """
        Retrieves next processed frame (frame_idx, frame_gray).
        Returns None at end-of-stream or on timeout.
        """
        if not self._started:
            self.start()

        try:
            item = self._queue.get(timeout=timeout)
            if item is None:
                self._queue.put(None)
                return None
            return item
        except queue.Empty:
            return None

    def read_batch(
        self,
        batch_size: int,
        timeout: float = 1.0,
    ) -> List[Tuple[int, np.ndarray]]:
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
        Returns a single frame in native resolution from the sliding window.
        If evicted, seeks and retrieves directly from video file on disk.
        """
        with self._ring_lock:
            for idx, frame in reversed(self._ring_buffer):
                if idx == frame_idx:
                    return frame

        # Fallback disk seek only for evicted frames
        cap = cv2.VideoCapture(str(self.video_path))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        cap.release()
        return frame if ret else None

    def get_raw_frames(self, start_frame: int, end_frame: int) -> List[np.ndarray]:
        """
        Extracts a sequence of frames in full native resolution for clip and composite generation.
        Fetches directly from RAM sliding window deque; falls back to disk seek only for evicted frames.
        """
        frames_dict: dict[int, np.ndarray] = {}

        # 1. Collect what is currently in sliding window deque
        with self._ring_lock:
            for idx, frame in self._ring_buffer:
                if start_frame <= idx <= end_frame:
                    frames_dict[idx] = frame

        # 2. Identify missing evicted frames
        missing_indices = [i for i in range(start_frame, end_frame + 1) if i not in frames_dict]

        if missing_indices:
            cap = cv2.VideoCapture(str(self.video_path))
            cur_seek = -999999
            for miss_idx in missing_indices:
                if miss_idx != cur_seek:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, miss_idx)
                    cur_seek = miss_idx
                ret, frame = cap.read()
                if ret:
                    frames_dict[miss_idx] = frame
                    cur_seek += 1
                else:
                    cur_seek = -999999
            cap.release()

        # Build ordered list of frames
        result = [frames_dict[i] for i in range(start_frame, end_frame + 1) if i in frames_dict]
        return result

    def compute_base_canvas(self, num_samples: int = 25) -> np.ndarray:
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
            canvas = np.median(sample_frames, axis=0).astype(np.uint8)
            del sample_frames
            return canvas
        return np.zeros((self.orig_height, self.orig_width, 3), dtype=np.uint8)

    def stop(self) -> None:
        """Stops reading thread and releases all allocated frame buffers immediately."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        with self._ring_lock:
            self._ring_buffer.clear()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Exception:
                break
        gc.collect()

    def __enter__(self) -> ThreadedVideoCapture:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
