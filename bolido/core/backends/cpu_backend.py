"""
Vectorized multi-threaded CPU backend utilizing OpenCV thread pooling and NumPy.
"""

from __future__ import annotations

import os
from typing import List, Optional

import cv2
import numpy as np

from bolido.core.backends.base import BaseBackend
from bolido.core.models import CandidateDetection


class CPUBackend(BaseBackend):
    """CPU compute backend leveraging all available physical and logical cores."""

    def __init__(self, device_info: str = "CPU", num_threads: int = 0):
        super().__init__(device_info=device_info)
        self.num_threads = num_threads
        self._configure_threads()

        self.bg_model: Optional[np.ndarray] = None
        self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

    def _configure_threads(self) -> None:
        """Configures OpenCV thread pool to utilize all CPU cores."""
        if self.num_threads > 0:
            cv2.setNumThreads(self.num_threads)
        else:
            # By default employ all CPU cores
            avail = cv2.getNumberOfCPUs()
            cv2.setNumThreads(avail)

    @property
    def name(self) -> str:
        return f"CPU (NumPy/OpenCV, {cv2.getNumThreads()} threads)"

    def initialize(
        self,
        width: int,
        height: int,
        learning_rate: float = 0.05,
        threshold: float = 35.0,
    ) -> None:
        super().initialize(width, height, learning_rate, threshold)
        self._configure_threads()
        self.bg_model = None

    def process_frame(
        self,
        frame_gray: np.ndarray,
        frame_idx: int,
    ) -> List[CandidateDetection]:
        """Runs differential frame analysis and contour extraction on CPU."""
        gray_f32 = frame_gray.astype(np.float32)

        # 1. Update background model
        if self.bg_model is None:
            self.bg_model = gray_f32.copy()
        else:
            cv2.accumulateWeighted(gray_f32, self.bg_model, self.learning_rate)

        # 2. Compute absolute difference against dynamic background
        bg_uint8 = cv2.convertScaleAbs(self.bg_model)
        diff = cv2.absdiff(frame_gray, bg_uint8)

        # Fast screening: check if maximum pixel difference reaches threshold
        # Uses vectorized NumPy reduction without GIL bottlenecks
        if np.max(diff) < self.threshold:
            return []

        # 3. Binary thresholding & morphological noise opening
        _, thresh = cv2.threshold(diff, self.threshold, 255, cv2.THRESH_BINARY)
        thresh_clean = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, self.morph_kernel)

        # 4. Extract candidate contours
        contours, _ = cv2.findContours(thresh_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        frame_candidates: List[CandidateDetection] = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Filter subpixel noise (< 3) and massive non-meteor flashes (> 3500)
            if area < 3 or area > 3500:
                continue

            (cx, cy), (w, h), angle = cv2.minAreaRect(cnt)
            major_axis = max(w, h)
            minor_axis = min(w, h)
            aspect_ratio = major_axis / max(minor_axis, 1.0)
            bx, by, bw, bh = cv2.boundingRect(cnt)

            # Streak condition: elongated streak OR moving spot of minimum diameter
            if major_axis >= 5.0 or aspect_ratio >= 1.3:
                roi_diff = diff[by : by + bh, bx : bx + bw]
                peak_val = float(np.max(roi_diff)) if roi_diff.size > 0 else 0.0

                frame_candidates.append(
                    CandidateDetection(
                        frame_idx=frame_idx,
                        centroid=(float(cx), float(cy)),
                        bbox=(bx, by, bw, bh),
                        major_axis=float(major_axis),
                        minor_axis=float(minor_axis),
                        aspect_ratio=float(aspect_ratio),
                        angle=float(angle),
                        contour=cnt,
                        peak_brightness=peak_val,
                    )
                )

        return frame_candidates

    def reset(self) -> None:
        self.bg_model = None
