"""
Base interface and device management for computation backends.
"""

from __future__ import annotations

import multiprocessing
import os
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

import cv2
import numpy as np

from bolido.config import DeviceConfig, DeviceType
from bolido.core.models import CandidateDetection


class BaseBackend(ABC):
    """Abstract base class for frame differencing and screening backends."""

    def __init__(self, device_info: str = "Unknown"):
        self.device_info = device_info
        self.width: int = 0
        self.height: int = 0
        self.learning_rate: float = 0.05
        self.threshold: float = 35.0

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name identifier (e.g. 'CPU (NumPy/OpenCV)', 'GPU (PyTorch/CUDA)')."""
        pass

    @abstractmethod
    def initialize(
        self,
        width: int,
        height: int,
        learning_rate: float = 0.05,
        threshold: float = 35.0,
    ) -> None:
        """Initializes backend state and allocates buffers for given resolution."""
        self.width = width
        self.height = height
        self.learning_rate = learning_rate
        self.threshold = threshold

    @abstractmethod
    def process_frame(
        self,
        frame_gray: np.ndarray,
        frame_idx: int,
    ) -> List[CandidateDetection]:
        """Processes a single grayscale frame and extracts candidate detections."""
        pass

    def process_batch(
        self,
        frames_gray: List[np.ndarray],
        start_frame_idx: int,
    ) -> List[List[CandidateDetection]]:
        """
        Processes a sequence of grayscale frames.
        Default implementation iterates over frames; GPU backend overrides with batch tensor math.
        """
        results: List[List[CandidateDetection]] = []
        for i, frame in enumerate(frames_gray):
            dets = self.process_frame(frame, start_frame_idx + i)
            results.append(dets)
        return results

    @abstractmethod
    def reset(self) -> None:
        """Clears background model and allocated memory buffers."""
        pass


class DeviceManager:
    """Detects available hardware compute backends and instantiates matching backends."""

    @staticmethod
    def is_cuda_available() -> Tuple[bool, str]:
        """Checks if PyTorch with CUDA support is installed and operational."""
        try:
            import torch
            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                return True, f"CUDA ({device_name})"
        except Exception:
            pass
        return False, ""

    @classmethod
    def get_device_info(cls, config: Optional[DeviceConfig] = None) -> Tuple[DeviceType, str]:
        """Resolves active device type and descriptive label."""
        req_type = config.device_type if config else DeviceType.AUTO
        cuda_ok, cuda_name = cls.is_cuda_available()

        if req_type == DeviceType.CUDA:
            if cuda_ok:
                return DeviceType.CUDA, cuda_name
            # Fallback to CPU if CUDA was requested but not available
            num_threads = config.num_cpu_threads if config and config.num_cpu_threads > 0 else (os.cpu_count() or 4)
            return DeviceType.CPU, f"CPU ({num_threads} threads) [CUDA unavailable]"

        if req_type == DeviceType.AUTO:
            if cuda_ok:
                return DeviceType.CUDA, cuda_name
            num_threads = config.num_cpu_threads if config and config.num_cpu_threads > 0 else (os.cpu_count() or 4)
            return DeviceType.CPU, f"CPU ({num_threads} threads)"

        # Explicit CPU
        num_threads = config.num_cpu_threads if config and config.num_cpu_threads > 0 else (os.cpu_count() or 4)
        return DeviceType.CPU, f"CPU ({num_threads} threads)"

    @classmethod
    def create_backend(
        cls,
        config: DeviceConfig,
        width: int,
        height: int,
        learning_rate: float = 0.05,
        threshold: float = 35.0,
    ) -> BaseBackend:
        """Instantiates and initializes the optimal backend according to config."""
        dev_type, dev_info = cls.get_device_info(config)

        if dev_type == DeviceType.CUDA:
            try:
                from bolido.core.backends.gpu_backend import GPUBackend
                backend = GPUBackend(device_info=dev_info)
                backend.initialize(width, height, learning_rate, threshold)
                return backend
            except Exception as e:
                # Safe fallback to CPU
                num_threads = config.num_cpu_threads if config.num_cpu_threads > 0 else (os.cpu_count() or 4)
                dev_info = f"CPU ({num_threads} threads) [Fallback: {e}]"

        from bolido.core.backends.cpu_backend import CPUBackend
        backend = CPUBackend(device_info=dev_info, num_threads=config.num_cpu_threads)
        backend.initialize(width, height, learning_rate, threshold)
        return backend
