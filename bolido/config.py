"""
Configuration dataclasses and settings for BOLIDO.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DeviceType(str, Enum):
    AUTO = "auto"
    CUDA = "cuda"
    CPU = "cpu"


@dataclass
class DeviceConfig:
    """Hardware acceleration and device configuration."""
    device_type: DeviceType = DeviceType.AUTO
    batch_size: int = 8
    num_cpu_threads: int = 0  # 0 = use all available CPU cores (cv2.getNumberOfCPUs())
    target_width: int = 1280  # Downscale detection pass width (0 or None = native resolution)


@dataclass
class DetectionConfig:
    """Core detection, tracking and filtering parameters."""
    threshold: float = 35.0
    min_length: float = 15.0
    buffer_sec: float = 1.5
    learning_rate: float = 0.05
    min_frames: int = 2
    max_frames: int = 25
    max_gap_frames: int = 2
    max_speed_px_per_frame: float = 180.0
    min_straightness: float = 0.65
    max_orthogonal_residual_px: float = 4.5
    save_clean: bool = True
    show_preview: bool = False
    device: DeviceConfig = field(default_factory=DeviceConfig)

    @property
    def clip_buffer_sec(self) -> float:
        return self.buffer_sec

    @clip_buffer_sec.setter
    def clip_buffer_sec(self, val: float):
        self.buffer_sec = float(val)
