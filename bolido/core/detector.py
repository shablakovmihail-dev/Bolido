"""
Meteor Detector - Orchestrator of video decoding, compute backends, astrometric validation,
and on-the-fly streaming event export.
Completely independent from GUI and Qt.
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from bolido.config import DetectionConfig, DeviceConfig
from bolido.core.backends.base import BaseBackend, DeviceManager
from bolido.core.models import CandidateDetection, MeteorEvent
from bolido.io.reader import ThreadedVideoCapture
from bolido.io.video_writer import AsyncVideoExporter, VideoExporter, safe_imwrite


class MeteorTracker:
    """
    Associates single-frame detections into multi-frame tracks and evaluates them
    against physical meteor kinematics and astrophotometric criteria.
    Supports on-the-fly extraction of finalized tracks as soon as post-buffers elapse.
    """

    def __init__(
        self,
        fps: float,
        min_length_px: float = 15.0,
        min_frames: int = 2,
        max_frames: int = 25,
        max_gap_frames: int = 2,
        max_speed_px_per_frame: float = 180.0,
        min_straightness: float = 0.65,
        max_orthogonal_residual_px: float = 4.5,
    ):
        self.fps = fps
        self.min_length_px = min_length_px
        self.min_frames = min_frames
        self.max_frames = max_frames
        self.max_gap_frames = max_gap_frames
        self.max_speed_px_per_frame = max_speed_px_per_frame
        self.min_straightness = min_straightness
        self.max_orthogonal_residual_px = max_orthogonal_residual_px

        self._active_events: List[MeteorEvent] = []
        self._closed_events: List[MeteorEvent] = []
        self._raw_counter: int = 0
        self._validated_counter: int = 0

    def update(self, frame_idx: int, frame_detections: List[CandidateDetection]) -> None:
        """Updates active tracks with detections from current frame."""
        unmatched_detections = list(frame_detections)

        # 1. Match candidates to active tracks based on spatial proximity & directional consistency
        for event in self._active_events:
            last_det = event.detections[-1]
            dt = frame_idx - last_det.frame_idx
            if dt <= 0:
                continue

            best_match: Optional[CandidateDetection] = None
            best_dist = float("inf")

            for cand in unmatched_detections:
                dist = math.hypot(
                    cand.centroid[0] - last_det.centroid[0],
                    cand.centroid[1] - last_det.centroid[1],
                )
                max_allowed_dist = self.max_speed_px_per_frame * dt

                if dist <= max_allowed_dist and dist < best_dist:
                    if len(event.detections) >= 2:
                        prev_p = np.array(event.detections[-2].centroid)
                        curr_p = np.array(last_det.centroid)
                        next_p = np.array(cand.centroid)
                        v1 = curr_p - prev_p
                        v2 = next_p - curr_p
                        norm1 = np.linalg.norm(v1)
                        norm2 = np.linalg.norm(v2)
                        if norm1 > 1.5 and norm2 > 1.5:
                            cos_angle = float(np.dot(v1, v2) / (norm1 * norm2))
                            if cos_angle < 0.2:  # Rejects erratic turns
                                continue

                    best_dist = dist
                    best_match = cand

            if best_match is not None:
                event.detections.append(best_match)
                event.end_frame = frame_idx
                event.last_seen_frame = frame_idx
                unmatched_detections.remove(best_match)

        # 2. Spawn new tracks for remaining unmatched detections
        for cand in unmatched_detections:
            self._raw_counter += 1
            new_event = MeteorEvent(
                event_id=self._raw_counter,
                start_frame=frame_idx,
                end_frame=frame_idx,
                detections=[cand],
                last_seen_frame=frame_idx,
            )
            self._active_events.append(new_event)

        # 3. Timeout stale tracks and move to closed list
        still_active: List[MeteorEvent] = []
        for event in self._active_events:
            if (frame_idx - event.last_seen_frame) > self.max_gap_frames:
                self._closed_events.append(event)
            else:
                still_active.append(event)
        self._active_events = still_active

    def extract_ready_events(self, current_frame_idx: int, buffer_frames: int) -> List[MeteorEvent]:
        """
        Extracts validated events whose post-buffer has fully elapsed in the stream.
        Enables streaming export without waiting for video EOF.
        """
        ready: List[MeteorEvent] = []
        unready: List[MeteorEvent] = []

        for event in self._closed_events:
            # Check if post-buffer is fully decoded and stored in reader's ring buffer
            if current_frame_idx >= (event.end_frame + buffer_frames):
                event.compute_metrics(self.fps)
                if self._validate_meteor(event):
                    self._validated_counter += 1
                    event.event_id = self._validated_counter
                    ready.append(event)
            else:
                unready.append(event)

        self._closed_events = unready
        return ready

    def finalize(self) -> List[MeteorEvent]:
        """Closes all remaining tracks and filters for true meteor events at stream end."""
        self._closed_events.extend(self._active_events)
        self._active_events.clear()

        valid_meteors: List[MeteorEvent] = []
        for event in self._closed_events:
            event.compute_metrics(self.fps)
            if self._validate_meteor(event):
                self._validated_counter += 1
                event.event_id = self._validated_counter
                valid_meteors.append(event)

        self._closed_events.clear()
        return valid_meteors

    def _validate_meteor(self, event: MeteorEvent) -> bool:
        """Physical meteor criteria: duration, track length, non-stationary, collinearity."""
        if not (self.min_frames <= event.duration_frames <= self.max_frames):
            return False

        if event.approx_length_px < self.min_length_px:
            return False

        p_first = np.array(event.detections[0].centroid)
        p_last = np.array(event.detections[-1].centroid)
        net_disp = float(np.linalg.norm(p_last - p_first))
        bbox_w, bbox_h = event.trajectory_bbox[2], event.trajectory_bbox[3]

        if event.duration_frames >= 3 and net_disp < 4.0 and max(bbox_w, bbox_h) < 6.0:
            return False  # Stationary star / hot pixel

        centroids = [d.centroid for d in event.detections]
        if len(centroids) >= 3:
            path_segments = [
                math.hypot(c2[0] - c1[0], c2[1] - c1[1])
                for c1, c2 in zip(centroids[:-1], centroids[1:])
            ]
            total_path = sum(path_segments)
            if total_path > 0:
                straightness = net_disp / total_path
                if straightness < self.min_straightness:
                    return False

            pts = np.array(centroids, dtype=np.float32)
            pts_centered = pts - np.mean(pts, axis=0)
            _, _, vh = np.linalg.svd(pts_centered)
            normal_vector = vh[1]
            residuals = np.abs(np.dot(pts_centered, normal_vector))
            mean_residual = float(np.mean(residuals))

            if mean_residual > self.max_orthogonal_residual_px:
                return False

        return True


class MeteorDetector:
    """
    Main detection orchestrator coordinating asynchronous reader, hardware backends,
    and on-the-fly streaming background export.
    """

    def __init__(self, config: Optional[DetectionConfig] = None, **kwargs):
        if config is not None:
            self.config = config
        else:
            dev_cfg = kwargs.pop("device", DeviceConfig())
            self.config = DetectionConfig(device=dev_cfg, **kwargs)

        self.backend: Optional[BaseBackend] = None
        self.active_device_name: str = ""

    def process_video(
        self,
        video_path: Union[str, Path],
        output_dir: Union[str, Path] = "output",
        progress_callback: Optional[Callable[[int, int, float, float], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        event_callback: Optional[Callable[[MeteorEvent], None]] = None,
    ) -> List[MeteorEvent]:
        """Runs the complete detection pipeline on a video file with on-the-fly streaming export."""
        video_path = Path(video_path)
        output_dir = Path(output_dir)
        video_out_dir = output_dir / f"{video_path.stem}_analysis"
        video_out_dir.mkdir(parents=True, exist_ok=True)

        # 1. Initialize threaded reader with dynamic buffer sizing
        target_w = self.config.device.target_width if self.config.device else 1280
        reader = ThreadedVideoCapture(
            video_path=video_path,
            target_width=target_w,
            buffer_sec=self.config.buffer_sec,
            max_expected_meteor_duration=self.config.max_frames,
        )
        total_frames = reader.total_frames
        fps = reader.fps
        orig_w, orig_h = reader.orig_width, reader.orig_height
        proc_w, proc_h = reader.proc_width, reader.proc_height
        scale_x, scale_y = reader.scale_x, reader.scale_y

        buffer_frames = reader.buffer_frames

        # 2. Initialize compute backend
        self.backend = DeviceManager.create_backend(
            self.config.device,
            width=proc_w,
            height=proc_h,
            learning_rate=self.config.learning_rate,
            threshold=self.config.threshold,
        )
        self.active_device_name = self.backend.device_info

        # 3. Base canvas for composite aggregation (median of initial frames in Full-Res)
        base_canvas = reader.compute_base_canvas(num_samples=25)

        # 4. Initialize asynchronous streaming exporter
        async_exporter = AsyncVideoExporter(
            output_dir=video_out_dir,
            video_name=video_path.name,
            fps=fps,
            width=orig_w,
            height=orig_h,
            base_canvas=base_canvas,
            save_clean=self.config.save_clean,
            event_callback=event_callback,
        )
        async_exporter.start()

        # 5. Prepare scaled tracker
        scale_factor = max(scale_x, scale_y)
        scaled_min_length = self.config.min_length / scale_factor
        scaled_speed = self.config.max_speed_px_per_frame / scale_factor

        tracker = MeteorTracker(
            fps=fps,
            min_length_px=scaled_min_length,
            min_frames=self.config.min_frames,
            max_frames=self.config.max_frames,
            max_gap_frames=self.config.max_gap_frames,
            max_speed_px_per_frame=scaled_speed,
            min_straightness=self.config.min_straightness,
            max_orthogonal_residual_px=self.config.max_orthogonal_residual_px,
        )

        batch_size = max(1, self.config.device.batch_size if self.config.device else 8)
        processed_frames = 0
        all_detected_events: List[MeteorEvent] = []
        t_start = time.time()

        reader.start()

        try:
            while True:
                if cancel_check and cancel_check():
                    break

                # Read batch of lightweight downscaled frames
                batch_items = reader.read_batch(batch_size=batch_size, timeout=1.0)
                if not batch_items:
                    break

                frames_gray = [item[1] for item in batch_items]
                start_frame_idx = batch_items[0][0]
                end_frame_idx = batch_items[-1][0]

                # Matrix screening on compute backend (GPU tensor batch or multi-threaded CPU)
                batch_detections = self.backend.process_batch(frames_gray, start_frame_idx)

                for (f_idx, _, _), frame_dets in zip(batch_items, batch_detections):
                    tracker.update(f_idx, frame_dets)

                processed_frames += len(batch_items)

                # On-the-fly streaming: check if any closed event's post-buffer has fully arrived
                ready_events = tracker.extract_ready_events(end_frame_idx, buffer_frames)
                for ev in ready_events:
                    # Rescale coordinates to Full-Res native resolution
                    if scale_x != 1.0 or scale_y != 1.0:
                        ev.scale_coordinates(scale_x, scale_y)

                    clip_start = max(0, ev.start_frame - buffer_frames)
                    clip_end = min(total_frames - 1, ev.end_frame + buffer_frames)

                    # Extract Full-Res pristine frames from RAM ring buffer
                    raw_clip_frames = reader.get_raw_frames(clip_start, clip_end)

                    # Dispatch to background exporter worker without blocking analysis
                    async_exporter.submit_event(ev, raw_clip_frames, clip_start, clip_end)
                    all_detected_events.append(ev)

                if progress_callback:
                    elapsed = max(0.001, time.time() - t_start)
                    cur_fps = processed_frames / elapsed
                    speed_mult = cur_fps / fps if fps > 0 else 1.0
                    progress_callback(processed_frames, total_frames, cur_fps, speed_mult)

            # Finalize remaining tracks at video stream conclusion
            trailing_events = tracker.finalize()
            for ev in trailing_events:
                if scale_x != 1.0 or scale_y != 1.0:
                    ev.scale_coordinates(scale_x, scale_y)

                clip_start = max(0, ev.start_frame - buffer_frames)
                clip_end = min(total_frames - 1, ev.end_frame + buffer_frames)

                raw_clip_frames = reader.get_raw_frames(clip_start, clip_end)
                async_exporter.submit_event(ev, raw_clip_frames, clip_start, clip_end)
                all_detected_events.append(ev)

        finally:
            reader.stop()
            if self.backend:
                self.backend.reset()

        # Wait for background video encoder to finish all queued clips and composites
        async_exporter.wait_complete()

        # Finalize full session master composite and tabular Excel/CSV reports
        async_exporter.finalize_session(total_frames)

        return all_detected_events
