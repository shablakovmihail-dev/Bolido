"""
CUDA/Tensor accelerated GPU compute backend using PyTorch.
Implements batched frame screening, background modeling, and thresholding directly on VRAM.
"""

from __future__ import annotations

from typing import List, Optional

import cv2
import numpy as np

from bolido.core.backends.base import BaseBackend
from bolido.core.models import CandidateDetection


class GPUBackend(BaseBackend):
    """
    Hardware-accelerated backend running batch matrix operations on NVIDIA CUDA tensors.
    """

    def __init__(self, device_info: str = "CUDA"):
        super().__init__(device_info=device_info)
        self._check_cuda()

        import torch
        self.torch = torch
        self.device = torch.device("cuda")
        self.bg_model: Optional[torch.Tensor] = None
        self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

    def _check_cuda(self) -> None:
        try:
            import torch
            if not torch.cuda.is_available():
                raise RuntimeError("PyTorch is installed, but CUDA is not available on this system.")
        except ImportError:
            raise RuntimeError("PyTorch with CUDA support is not installed.")

    @property
    def name(self) -> str:
        return f"GPU (PyTorch/CUDA: {self.device_info})"

    def initialize(
        self,
        width: int,
        height: int,
        learning_rate: float = 0.05,
        threshold: float = 35.0,
    ) -> None:
        super().initialize(width, height, learning_rate, threshold)
        self.bg_model = None
        if self.torch.cuda.is_available():
            self.torch.cuda.empty_cache()

    def process_frame(
        self,
        frame_gray: np.ndarray,
        frame_idx: int,
    ) -> List[CandidateDetection]:
        """Processes a single frame via GPU tensor screening."""
        res = self.process_batch([frame_gray], frame_idx)
        return res[0] if res else []

    def process_batch(
        self,
        frames_gray: List[np.ndarray],
        start_frame_idx: int,
    ) -> List[List[CandidateDetection]]:
        """
        Processes a mini-batch of grayscale frames on CUDA tensors.
        Screening, exponential moving average, absolute difference, and thresholding
        occur simultaneously in GPU VRAM to minimize PCIe transfers.
        """
        batch_size = len(frames_gray)
        if batch_size == 0:
            return []

        torch = self.torch

        # Transfer batch of frames to GPU memory: shape (B, H, W)
        batch_np = np.stack(frames_gray)
        batch_t = torch.from_numpy(batch_np).to(device=self.device, dtype=torch.float32, non_blocking=True)

        batch_results: List[List[CandidateDetection]] = []

        with torch.no_grad():
            for b in range(batch_size):
                cur_frame_t = batch_t[b]
                frame_idx = start_frame_idx + b

                # Update background model on GPU
                if self.bg_model is None:
                    self.bg_model = cur_frame_t.clone()
                else:
                    # Lerp: bg = (1 - alpha) * bg + alpha * frame
                    self.bg_model.lerp_(cur_frame_t, self.learning_rate)

                # Absolute difference
                diff_t = torch.abs(cur_frame_t - self.bg_model)

                # Fast screening on GPU: check if any pixel exceeds threshold
                max_diff = torch.max(diff_t).item()
                if max_diff < self.threshold:
                    batch_results.append([])
                    continue

                # Thresholding directly on GPU
                mask_t = (diff_t >= self.threshold).to(torch.uint8) * 255

                # Transfer only sparse candidate frames back to CPU for contour geometry
                diff_np = diff_t.to(torch.uint8).cpu().numpy()
                mask_np = mask_t.cpu().numpy()

                # Morphological noise opening on CPU
                thresh_clean = cv2.morphologyEx(mask_np, cv2.MORPH_OPEN, self.morph_kernel)

                # Extract geometric contours
                contours, _ = cv2.findContours(thresh_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                frame_candidates: List[CandidateDetection] = []

                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if area < 3 or area > 3500:
                        continue

                    (cx, cy), (w, h), angle = cv2.minAreaRect(cnt)
                    major_axis = max(w, h)
                    minor_axis = min(w, h)
                    aspect_ratio = major_axis / max(minor_axis, 1.0)
                    bx, by, bw, bh = cv2.boundingRect(cnt)

                    if major_axis >= 5.0 or aspect_ratio >= 1.3:
                        roi_diff = diff_np[by : by + bh, bx : bx + bw]
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

                batch_results.append(frame_candidates)

        return batch_results

    def reset(self) -> None:
        self.bg_model = None
        if self.torch.cuda.is_available():
            self.torch.cuda.empty_cache()
