"""
Video writer, asynchronous image exporter, and reporting utilities.
Decoupled from GUI and core detection algorithms.
"""

from __future__ import annotations

import csv
import math
import queue
import threading
from pathlib import Path
from typing import Callable, List, Optional, Union

import cv2
import numpy as np

from bolido.core.models import MeteorEvent


def safe_imwrite(file_path: Union[str, Path], img: np.ndarray, params=None) -> bool:
    """Writes an image to disk safely on all platforms, including Windows paths with Unicode."""
    try:
        if params is None:
            params = [cv2.IMWRITE_JPEG_QUALITY, 95]
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        ext = p.suffix or ".jpg"
        success, buf = cv2.imencode(ext, img, params)
        if success:
            with open(str(p), "wb") as f:
                f.write(buf)
            return True
        return False
    except Exception:
        return False


class VideoExporter:
    """Synchronous / standalone video and composite exporter."""

    def __init__(self, save_clean: bool = True, buffer_sec: float = 1.5):
        self.save_clean = save_clean
        self.buffer_sec = buffer_sec

    def export_events(
        self,
        video_path: Path,
        output_dir: Path,
        events: List[MeteorEvent],
        fps: float,
        total_frames: int,
        width: int,
        height: int,
        base_canvas: Optional[np.ndarray] = None,
        progress_cb=None,
    ) -> None:
        """Extracts MP4 clips, raw frames, max-merge images, full-session master composites, and reports."""
        buffer_frames = int(round(self.buffer_sec * fps))

        raw_frames_dir = output_dir / "raw_frames"
        composites_dir = output_dir / "composites"
        clips_dir = output_dir / "clips"

        raw_frames_dir.mkdir(parents=True, exist_ok=True)
        composites_dir.mkdir(parents=True, exist_ok=True)
        clips_dir.mkdir(parents=True, exist_ok=True)

        if base_canvas is not None:
            master_raw = base_canvas.copy()
        else:
            master_raw = np.zeros((height, width, 3), dtype=np.uint8)

        for event in events:
            event.clip_start_frame = max(0, event.start_frame - buffer_frames)
            event.clip_end_frame = min(total_frames - 1, event.end_frame + buffer_frames)

        cap = cv2.VideoCapture(str(video_path))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        for idx, event in enumerate(events, start=1):
            if progress_cb:
                progress_cb(idx, len(events))

            cap.set(cv2.CAP_PROP_POS_FRAMES, event.clip_start_frame)
            current_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

            while current_pos < event.clip_start_frame:
                ret = cap.grab()
                if not ret:
                    break
                current_pos += 1

            clip_filename = clips_dir / f"event_{event.event_id:03d}.mp4"
            writer = cv2.VideoWriter(str(clip_filename), fourcc, fps, (width, height))

            event_frames: List[np.ndarray] = []
            frame_cursor = event.clip_start_frame

            while frame_cursor <= event.clip_end_frame:
                ret, frame = cap.read()
                if not ret:
                    break

                writer.write(frame)

                if event.start_frame <= frame_cursor <= event.end_frame:
                    event_frames.append(frame.copy())
                    raw_path = raw_frames_dir / f"event_{event.event_id:03d}_frame_{frame_cursor:05d}.jpg"
                    safe_imwrite(raw_path, frame)
                    event.raw_frames.append(str(raw_path))

                frame_cursor += 1

            writer.release()
            event.clip_path = str(clip_filename)

            if event_frames:
                max_merge = np.maximum.reduce(event_frames)

                if self.save_clean:
                    clean_path = composites_dir / f"event_{event.event_id:03d}_clean.jpg"
                    safe_imwrite(clean_path, max_merge)
                    event.clean_merge_path = str(clean_path)

                annotated = self.draw_event_annotation(max_merge, event)
                annotated_path = composites_dir / f"event_{event.event_id:03d}_max_merge.jpg"
                safe_imwrite(annotated_path, annotated)
                event.max_merge_path = str(annotated_path)

                # Transient Merging onto Master Raw Canvas
                bx, by, bw, bh = event.trajectory_bbox
                pad = max(24, int(max(bw, bh) * 0.35))
                x1 = max(0, bx - pad)
                y1 = max(0, by - pad)
                x2 = min(width, bx + bw + pad)
                y2 = min(height, by + bh + pad)

                roi_base = master_raw[y1:y2, x1:x2]
                roi_event = max_merge[y1:y2, x1:x2]

                diff_roi = cv2.absdiff(
                    cv2.cvtColor(roi_event, cv2.COLOR_BGR2GRAY),
                    cv2.cvtColor(roi_base, cv2.COLOR_BGR2GRAY),
                )
                mask = (diff_roi > 12) & (
                    cv2.cvtColor(roi_event, cv2.COLOR_BGR2GRAY) > cv2.cvtColor(roi_base, cv2.COLOR_BGR2GRAY)
                )
                roi_base[mask] = np.maximum(roi_base[mask], roi_event[mask])
                master_raw[y1:y2, x1:x2] = roi_base

        cap.release()

        # Session master composites
        master_raw_path = composites_dir / "master_composite_raw.jpg"
        safe_imwrite(master_raw_path, master_raw)

        master_annotated = self.draw_master_composite_annotation(
            master_raw, events, video_path.name, total_frames / fps, fps
        )
        master_annotated_path = composites_dir / "master_composite_annotated.jpg"
        safe_imwrite(master_annotated_path, master_annotated)

        # Tabular reports
        xlsx_path = output_dir / "detections.xlsx"
        self.save_xlsx(xlsx_path, events, fps)

        csv_path = output_dir / "detections.csv"
        self.save_csv(csv_path, events, fps)

    @staticmethod
    def draw_event_annotation(image: np.ndarray, event: MeteorEvent) -> np.ndarray:
        """Renders bounding box, trajectory marker, and information banner in calm graphite/indigo palette."""
        annotated = image.copy()
        img_h, img_w = annotated.shape[:2]

        if event.detections:
            p_first = (int(event.detections[0].centroid[0]), int(event.detections[0].centroid[1]))
            p_last = (int(event.detections[-1].centroid[0]), int(event.detections[-1].centroid[1]))
            cv2.line(annotated, p_first, p_last, (235, 195, 145), 1, cv2.LINE_AA)

        bx, by, bw, bh = event.trajectory_bbox
        pad = max(12, int(min(bw, bh) * 0.3))
        x1 = max(0, bx - pad)
        y1 = max(0, by - pad)
        x2 = min(img_w - 1, bx + bw + pad)
        y2 = min(img_h - 1, by + bh + pad)

        color_box = (246, 130, 59)
        bracket_len = min(15, max(4, (x2 - x1) // 3), max(4, (y2 - y1) // 3))
        thickness = 2

        cv2.line(annotated, (x1, y1), (x1 + bracket_len, y1), color_box, thickness)
        cv2.line(annotated, (x1, y1), (x1, y1 + bracket_len), color_box, thickness)
        cv2.line(annotated, (x2, y1), (x2 - bracket_len, y1), color_box, thickness)
        cv2.line(annotated, (x2, y1), (x2, y1 + bracket_len), color_box, thickness)
        cv2.line(annotated, (x1, y2), (x1 + bracket_len, y2), color_box, thickness)
        cv2.line(annotated, (x1, y2), (x1, y2 - bracket_len), color_box, thickness)
        cv2.line(annotated, (x2, y2), (x2 - bracket_len, y2), color_box, thickness)
        cv2.line(annotated, (x2, y2), (x2, y2 - bracket_len), color_box, thickness)

        card_x, card_y = 20, 20
        card_w, card_h = 260, 95
        overlay = annotated.copy()
        cv2.rectangle(overlay, (card_x, card_y), (card_x + card_w, card_y + card_h), (28, 32, 44), -1)
        cv2.rectangle(overlay, (card_x, card_y), (card_x + card_w, card_y + card_h), (68, 50, 43), 1)
        cv2.addWeighted(overlay, 0.85, annotated, 0.15, 0, annotated)

        info_lines = [
            f"EVENT #{event.event_id:03d}",
            f"Time: {event.start_time_sec:.2f}s - {event.end_time_sec:.2f}s",
            f"Frames: {event.duration_frames} ({event.start_frame}..{event.end_frame})",
            f"Est. Length: {event.approx_length_px:.1f} px",
        ]

        font = cv2.FONT_HERSHEY_SIMPLEX
        for i, line in enumerate(info_lines):
            line_y = card_y + 20 + i * 20
            color = (246, 160, 90) if i == 0 else (226, 232, 240)
            cv2.putText(annotated, line, (card_x + 10, line_y), font, 0.45, color, 1, cv2.LINE_AA)

        return annotated

    @staticmethod
    def draw_master_composite_annotation(
        image: np.ndarray,
        events: List[MeteorEvent],
        video_name: str,
        duration_sec: float,
        fps: float,
    ) -> np.ndarray:
        """Renders vector annotations for all detected meteors and session summary banner in graphite & indigo palette."""
        annotated = image.copy()
        img_h, img_w = annotated.shape[:2]

        for ev in events:
            if not ev.detections:
                continue

            p_first = (int(ev.detections[0].centroid[0]), int(ev.detections[0].centroid[1]))
            p_last = (int(ev.detections[-1].centroid[0]), int(ev.detections[-1].centroid[1]))
            cv2.line(annotated, p_first, p_last, (250, 165, 96), 1, cv2.LINE_AA)

            bx, by, bw, bh = ev.trajectory_bbox
            pad = max(10, int(min(bw, bh) * 0.25))
            x1 = max(0, bx - pad)
            y1 = max(0, by - pad)
            x2 = min(img_w - 1, bx + bw + pad)
            y2 = min(img_h - 1, by + bh + pad)

            bracket_len = min(12, max(3, (x2 - x1) // 3), max(3, (y2 - y1) // 3))
            color_box = (246, 130, 59)
            thickness = 1

            cv2.line(annotated, (x1, y1), (x1 + bracket_len, y1), color_box, thickness)
            cv2.line(annotated, (x1, y1), (x1, y1 + bracket_len), color_box, thickness)
            cv2.line(annotated, (x2, y1), (x2 - bracket_len, y1), color_box, thickness)
            cv2.line(annotated, (x2, y1), (x2, y1 + bracket_len), color_box, thickness)
            cv2.line(annotated, (x1, y2), (x1 + bracket_len, y2), color_box, thickness)
            cv2.line(annotated, (x1, y2), (x1, y2 - bracket_len), color_box, thickness)
            cv2.line(annotated, (x2, y2), (x2 - bracket_len, y2), color_box, thickness)
            cv2.line(annotated, (x2, y2), (x2, y2 - bracket_len), color_box, thickness)

            start_m = int(ev.start_time_sec // 60)
            start_s = ev.start_time_sec % 60
            label_text = f"#{ev.event_id:03d} {start_m:02d}:{start_s:04.1f}s"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.38
            font_thick = 1
            (tw, th), baseline = cv2.getTextSize(label_text, font, font_scale, font_thick)

            pill_x = max(6, min(x1, img_w - tw - 12))
            pill_y = y1 - 6 if y1 - th - 10 > 0 else y2 + th + 12

            overlay_p = annotated.copy()
            cv2.rectangle(overlay_p, (pill_x - 4, pill_y - th - 4), (pill_x + tw + 4, pill_y + 4), (28, 32, 44), -1)
            cv2.rectangle(overlay_p, (pill_x - 4, pill_y - th - 4), (pill_x + tw + 4, pill_y + 4), (68, 50, 43), 1)
            cv2.addWeighted(overlay_p, 0.85, annotated, 0.15, 0, annotated)

            cv2.putText(annotated, label_text, (pill_x, pill_y), font, font_scale, (250, 165, 96), font_thick, cv2.LINE_AA)

        card_x, card_y = 20, 20
        card_w, card_h = 320, 105
        overlay = annotated.copy()
        cv2.rectangle(overlay, (card_x, card_y), (card_x + card_w, card_y + card_h), (28, 32, 44), -1)
        cv2.rectangle(overlay, (card_x, card_y), (card_x + card_w, card_y + card_h), (68, 50, 43), 1)
        cv2.line(overlay, (card_x, card_y), (card_x + card_w, card_y), (246, 130, 59), 2)
        cv2.addWeighted(overlay, 0.88, annotated, 0.12, 0, annotated)

        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(annotated, "BOLIDO SESSION MASTER COMPOSITE", (card_x + 14, card_y + 24), font, 0.44, (250, 165, 96), 1, cv2.LINE_AA)
        cv2.line(annotated, (card_x + 14, card_y + 32), (card_x + card_w - 14, card_y + 32), (55, 42, 35), 1)

        info_lines = [
            f"Source: {video_name}",
            f"Meteors Detected: {len(events)}",
            f"Video Duration: {duration_sec:.1f}s ({int(duration_sec*fps)} f @ {fps:.1f} FPS)",
        ]
        for i, line in enumerate(info_lines):
            line_y = card_y + 50 + i * 18
            cv2.putText(annotated, line, (card_x + 14, line_y), font, 0.38, (226, 232, 240), 1, cv2.LINE_AA)

        return annotated

    @staticmethod
    def save_xlsx(xlsx_path: Path, events: List[MeteorEvent], fps: float) -> None:
        """Saves styled Excel spreadsheet report."""
        try:
            import openpyxl
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Detections"
            ws.views.sheetView[0].showGridLines = True

            headers = [
                "Event ID",
                "Start Time (s)",
                "Formatted Time",
                "Duration",
                "Peak Intensity",
                "Estimated Track Length (px)",
                "Associated Clip Filename",
                "Associated Composite Filename",
            ]
            ws.append(headers)

            header_font = Font(name="Segoe UI", size=11, bold=True, color="F8FAFC")
            header_fill = PatternFill(start_color="1C202C", end_color="1C202C", fill_type="solid")
            center_align = Alignment(horizontal="center", vertical="center")
            thin_border = Border(
                left=Side(style="thin", color="2B3244"),
                right=Side(style="thin", color="2B3244"),
                top=Side(style="thin", color="2B3244"),
                bottom=Side(style="thin", color="2B3244"),
            )

            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_align
                cell.border = thin_border
            ws.row_dimensions[1].height = 26

            data_font = Font(name="Segoe UI", size=10, color="1E293B")

            for ev in events:
                start_m = int(ev.start_time_sec // 60)
                start_s = ev.start_time_sec % 60
                formatted_time = f"{start_m:02d}:{start_s:05.2f}"
                dur_sec = ev.duration_frames / fps if fps > 0 else 0.0
                duration_str = f"{dur_sec:.2f}s ({ev.duration_frames} f)"
                clip_name = Path(ev.clip_path).name if ev.clip_path else f"event_{ev.event_id:03d}.mp4"
                comp_name = Path(ev.max_merge_path).name if ev.max_merge_path else f"event_{ev.event_id:03d}_max_merge.jpg"

                row_data = [
                    f"#{ev.event_id:03d}",
                    round(ev.start_time_sec, 2),
                    formatted_time,
                    duration_str,
                    round(ev.peak_intensity, 1),
                    round(ev.approx_length_px, 1),
                    clip_name,
                    comp_name,
                ]
                ws.append(row_data)
                cur_row = ws.max_row
                ws.row_dimensions[cur_row].height = 22
                for col_idx in range(1, len(row_data) + 1):
                    c = ws.cell(row=cur_row, column=col_idx)
                    c.font = data_font
                    c.alignment = center_align
                    c.border = thin_border
                    if col_idx in (2, 5, 6):
                        c.number_format = "0.00"

            ws.freeze_panes = "A2"

            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

            wb.save(xlsx_path)
        except Exception as e:
            print(f"[WARNING] Could not save Excel report: {e}")

    @staticmethod
    def save_csv(csv_path: Path, events: List[MeteorEvent], fps: float) -> None:
        """Saves tabular detection summary log."""
        fieldnames = [
            "event_id",
            "start_time_sec",
            "formatted_time",
            "duration_frames",
            "duration_sec",
            "peak_intensity",
            "approx_length_px",
            "clip_filename",
            "composite_filename",
        ]
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for ev in events:
                start_m = int(ev.start_time_sec // 60)
                start_s = ev.start_time_sec % 60
                writer.writerow(
                    {
                        "event_id": f"#{ev.event_id:03d}",
                        "start_time_sec": f"{ev.start_time_sec:.2f}",
                        "formatted_time": f"{start_m:02d}:{start_s:05.2f}",
                        "duration_frames": ev.duration_frames,
                        "duration_sec": f"{ev.duration_frames / fps:.2f}" if fps > 0 else "0.00",
                        "peak_intensity": f"{ev.peak_intensity:.1f}",
                        "approx_length_px": f"{ev.approx_length_px:.1f}",
                        "clip_filename": Path(ev.clip_path).name if ev.clip_path else "",
                        "composite_filename": Path(ev.max_merge_path).name if ev.max_merge_path else "",
                    }
                )


class AsyncVideoExporter:
    """
    On-the-fly streaming exporter. Encodes MP4 clips, pristine Full-Res max merges,
    and updates the session master canvas in a background thread concurrently with detection.
    """

    def __init__(
        self,
        output_dir: Path,
        video_name: str,
        fps: float,
        width: int,
        height: int,
        base_canvas: np.ndarray,
        save_clean: bool = True,
        event_callback: Optional[Callable[[MeteorEvent], None]] = None,
    ):
        self.output_dir = output_dir
        self.video_name = video_name
        self.fps = fps
        self.width = width
        self.height = height
        self.save_clean = save_clean
        self.event_callback = event_callback

        # Destination directories
        self.raw_frames_dir = self.output_dir / "raw_frames"
        self.composites_dir = self.output_dir / "composites"
        self.clips_dir = self.output_dir / "clips"

        self.raw_frames_dir.mkdir(parents=True, exist_ok=True)
        self.composites_dir.mkdir(parents=True, exist_ok=True)
        self.clips_dir.mkdir(parents=True, exist_ok=True)

        # Session master canvas
        self.master_raw = base_canvas.copy()
        self._master_lock = threading.Lock()

        # Queue and background worker thread
        self._queue: queue.Queue = queue.Queue()
        self._exported_events: List[MeteorEvent] = []
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="AsyncVideoExporter")
        self._stop_event = threading.Event()
        self._started = False

    def start(self) -> AsyncVideoExporter:
        if not self._started:
            self._started = True
            self._worker_thread.start()
        return self

    def submit_event(
        self,
        event: MeteorEvent,
        raw_frames: List[np.ndarray],
        clip_start_frame: int,
        clip_end_frame: int,
    ) -> None:
        """Submits an event task with Full-Res raw frames for background encoding."""
        if not self._started:
            self.start()
        self._queue.put((event, raw_frames, clip_start_frame, clip_end_frame))

    def _worker_loop(self) -> None:
        """Background worker loop encoding video clips and computing composites."""
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        while True:
            item = self._queue.get()
            if item is None:
                self._queue.task_done()
                break

            event, raw_frames, clip_start_frame, clip_end_frame = item
            event.clip_start_frame = clip_start_frame
            event.clip_end_frame = clip_end_frame

            try:
                # 1. Encode MP4 clip in Full Resolution
                clip_filename = self.clips_dir / f"event_{event.event_id:03d}.mp4"
                writer = cv2.VideoWriter(str(clip_filename), fourcc, self.fps, (self.width, self.height))

                event_frames: List[np.ndarray] = []

                for cursor_idx, frame in enumerate(raw_frames, start=clip_start_frame):
                    writer.write(frame)

                    # Save raw frames for the meteor flash interval
                    if event.start_frame <= cursor_idx <= event.end_frame:
                        event_frames.append(frame.copy())
                        raw_path = self.raw_frames_dir / f"event_{event.event_id:03d}_frame_{cursor_idx:05d}.jpg"
                        safe_imwrite(raw_path, frame)
                        event.raw_frames.append(str(raw_path))

                writer.release()
                event.clip_path = str(clip_filename)

                # 2. Compute Max-Pixel Merge in Full Resolution
                if event_frames:
                    max_merge = np.maximum.reduce(event_frames)

                    if self.save_clean:
                        clean_path = self.composites_dir / f"event_{event.event_id:03d}_clean.jpg"
                        safe_imwrite(clean_path, max_merge)
                        event.clean_merge_path = str(clean_path)

                    annotated = VideoExporter.draw_event_annotation(max_merge, event)
                    annotated_path = self.composites_dir / f"event_{event.event_id:03d}_max_merge.jpg"
                    safe_imwrite(annotated_path, annotated)
                    event.max_merge_path = str(annotated_path)

                    # 3. Incrementally merge onto session master raw canvas
                    with self._master_lock:
                        bx, by, bw, bh = event.trajectory_bbox
                        pad = max(24, int(max(bw, bh) * 0.35))
                        x1 = max(0, bx - pad)
                        y1 = max(0, by - pad)
                        x2 = min(self.width, bx + bw + pad)
                        y2 = min(self.height, by + bh + pad)

                        roi_base = self.master_raw[y1:y2, x1:x2]
                        roi_event = max_merge[y1:y2, x1:x2]

                        diff_roi = cv2.absdiff(
                            cv2.cvtColor(roi_event, cv2.COLOR_BGR2GRAY),
                            cv2.cvtColor(roi_base, cv2.COLOR_BGR2GRAY),
                        )
                        mask = (diff_roi > 12) & (
                            cv2.cvtColor(roi_event, cv2.COLOR_BGR2GRAY) > cv2.cvtColor(roi_base, cv2.COLOR_BGR2GRAY)
                        )
                        roi_base[mask] = np.maximum(roi_base[mask], roi_event[mask])
                        self.master_raw[y1:y2, x1:x2] = roi_base

                self._exported_events.append(event)

                # 4. Notify UI immediately so event card appears on-the-fly!
                if self.event_callback:
                    try:
                        self.event_callback(event)
                    except Exception as cb_err:
                        print(f"[WARNING] Event callback failed: {cb_err}")

            except Exception as e:
                print(f"[ERROR] Failed exporting event #{event.event_id}: {e}")

            finally:
                self._queue.task_done()

    def wait_complete(self) -> None:
        """Blocks until all submitted events have finished encoding."""
        self._queue.join()

    def finalize_session(self, total_frames: int) -> Tuple[Path, Path]:
        """
        Finalizes session artifacts: saves master composite images and tabular reports.
        Must be called after wait_complete().
        """
        # Stop worker thread
        self._queue.put(None)
        self._worker_thread.join(timeout=3.0)

        duration_sec = total_frames / self.fps if self.fps > 0 else 0.0

        # Save session master composites
        master_raw_path = self.composites_dir / "master_composite_raw.jpg"
        safe_imwrite(master_raw_path, self.master_raw)

        master_annotated = VideoExporter.draw_master_composite_annotation(
            self.master_raw, self._exported_events, self.video_name, duration_sec, self.fps
        )
        master_annotated_path = self.composites_dir / "master_composite_annotated.jpg"
        safe_imwrite(master_annotated_path, master_annotated)

        # Save tabular reports
        xlsx_path = self.output_dir / "detections.xlsx"
        VideoExporter.save_xlsx(xlsx_path, self._exported_events, self.fps)

        csv_path = self.output_dir / "detections.csv"
        VideoExporter.save_csv(csv_path, self._exported_events, self.fps)

        return master_raw_path, master_annotated_path
