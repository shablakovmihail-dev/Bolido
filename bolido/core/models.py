"""
Data models and geometric structures for detections and meteor events.
Completely decoupled from GUI and I/O.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import numpy as np


@dataclass(frozen=True)
class Point:
    """2D coordinate representation."""
    x: float
    y: float

    def as_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def as_int_tuple(self) -> Tuple[int, int]:
        return (int(round(self.x)), int(round(self.y)))


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned 2D bounding box (x, y, width, height)."""
    x: int
    y: int
    w: int
    h: int

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    @property
    def center(self) -> Point:
        return Point(self.x + self.w / 2.0, self.y + self.h / 2.0)

    @property
    def diagonal(self) -> float:
        return math.hypot(self.w, self.h)

    def pad(self, padding: int, max_w: int, max_h: int) -> BoundingBox:
        x1 = max(0, self.x - padding)
        y1 = max(0, self.y - padding)
        x2 = min(max_w, self.x + self.w + padding)
        y2 = min(max_h, self.y + self.h + padding)
        return BoundingBox(x1, y1, max(0, x2 - x1), max(0, y2 - y1))


@dataclass
class CandidateDetection:
    """Represents a candidate streak or moving spot detected in a single frame."""
    frame_idx: int
    centroid: Tuple[float, float]
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    major_axis: float
    minor_axis: float
    aspect_ratio: float
    angle: float
    contour: Optional[np.ndarray] = None
    peak_brightness: float = 0.0


@dataclass
class MeteorEvent:
    """Represents a grouped and validated meteor trajectory across frames."""
    event_id: int
    start_frame: int
    end_frame: int
    detections: List[CandidateDetection] = field(default_factory=list)
    last_seen_frame: int = 0
    approx_length_px: float = 0.0
    start_time_sec: float = 0.0
    end_time_sec: float = 0.0
    duration_frames: int = 0
    peak_intensity: float = 0.0
    trajectory_bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    clip_start_frame: int = 0
    clip_end_frame: int = 0
    clip_path: Optional[str] = None
    max_merge_path: Optional[str] = None
    clean_merge_path: Optional[str] = None
    raw_frames: List[str] = field(default_factory=list)

    def compute_metrics(self, fps: float) -> None:
        """Calculates trajectory metrics, timings, and bounding boundaries."""
        if not self.detections:
            return

        self.start_frame = min(d.frame_idx for d in self.detections)
        self.end_frame = max(d.frame_idx for d in self.detections)
        self.duration_frames = self.end_frame - self.start_frame + 1
        self.start_time_sec = self.start_frame / fps
        self.end_time_sec = self.end_frame / fps
        self.peak_intensity = max((d.peak_brightness for d in self.detections), default=0.0)

        # Track trajectory bounding box
        min_x = min(d.bbox[0] for d in self.detections)
        min_y = min(d.bbox[1] for d in self.detections)
        max_x = max(d.bbox[0] + d.bbox[2] for d in self.detections)
        max_y = max(d.bbox[1] + d.bbox[3] for d in self.detections)
        self.trajectory_bbox = (min_x, min_y, max_x - min_x, max_y - min_y)

        # Net displacement between first and last detection centroids
        p_first = np.array(self.detections[0].centroid)
        p_last = np.array(self.detections[-1].centroid)
        net_displacement = float(np.linalg.norm(p_last - p_first))

        # Overall bounding box diagonal
        bbox_diagonal = math.hypot(self.trajectory_bbox[2], self.trajectory_bbox[3])

        # Mean single-frame streak length
        avg_streak = float(np.mean([d.major_axis for d in self.detections]))

        # Approximate full path length
        self.approx_length_px = round(max(net_displacement + avg_streak * 0.5, bbox_diagonal), 1)

    def scale_coordinates(self, scale_x: float, scale_y: float) -> None:
        """Scales coordinates from a downscaled detection pass back to native video coordinates."""
        if scale_x == 1.0 and scale_y == 1.0:
            return

        for det in self.detections:
            det.centroid = (det.centroid[0] * scale_x, det.centroid[1] * scale_y)
            bx, by, bw, bh = det.bbox
            det.bbox = (
                int(round(bx * scale_x)),
                int(round(by * scale_y)),
                int(round(bw * scale_x)),
                int(round(bh * scale_y)),
            )
            det.major_axis *= max(scale_x, scale_y)
            det.minor_axis *= min(scale_x, scale_y)
            if det.contour is not None:
                cnt = det.contour.astype(np.float32)
                cnt[:, :, 0] *= scale_x
                cnt[:, :, 1] *= scale_y
                det.contour = np.round(cnt).astype(np.int32)

        bx, by, bw, bh = self.trajectory_bbox
        self.trajectory_bbox = (
            int(round(bx * scale_x)),
            int(round(by * scale_y)),
            int(round(bw * scale_x)),
            int(round(bh * scale_y)),
        )
        self.approx_length_px = round(self.approx_length_px * max(scale_x, scale_y), 1)
