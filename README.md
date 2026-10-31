<div align="center">

<img src="assets/logo_raw.png" alt="Bolido Logo" width="160" />

# BOLIDO

**Offline Computer Vision Night Sky Video Analyzer & Meteor Detector**

[![Version](https://img.shields.io/badge/version-2.3.7-38BDF8?style=flat-square)](https://github.com/shablakovmihail-dev/Bolido/releases)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PySide6-41CD52?style=flat-square&logo=qt&logoColor=white)](https://pypi.org/project/PySide6/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

</div>

---

## Overview

**Bolido** is a high-performance offline desktop application engineered for automated detection, tracking, and cataloging of meteors, fireballs (*bolides*), and optical transients in night sky video recordings, all-sky camera feeds, and astrophotography timelapses.

Built with a decoupled computer vision pipeline, Bolido separates high-throughput detection from high-fidelity artifact extraction, delivering processing speeds exceeding 150+ FPS even during long, high-resolution astronomical observation sessions—completely offline and without any cloud dependencies.

---

## Key Features

- **High-Speed Asynchronous Reader (150+ FPS)**: Multi-threaded video decoding coupled with a bounded ring buffer that prevents disk I/O bottlenecks and continuously saturates the detection engine.
- **Dual-Resolution Pipeline**: Motion analysis, background modeling, and transient tracking run on downscaled frames (Low-Res), while video clips, raw frames, and composites are extracted and preserved in original Full-Res.
- **Automatic Backend Selection**: Dynamically detects available hardware and switches between NVIDIA CUDA acceleration (via PyTorch) and multi-threaded CPU execution with zero manual configuration.
- **Max-Merge & Session Master Composites**: Automatically accumulates localized temporal Max-Merge snapshots for individual events, alongside session-wide master composites (`master_composite_raw.jpg` and `master_composite_annotated.jpg`).
- **Structured Excel Reporting**: Generates standardized observation spreadsheets (`detections.xlsx`) with timestamps, peak intensities, trajectory coordinates, durations, and frame ranges.
- **Dark Minimal UI**: Sleek, distraction-free interface built with PySide6, featuring astro-themed styling, real-time hardware telemetry, an interactive video player, and responsive sliders.

---

## Project Structure

```text
bolido/
├── assets/                     # Application icons, logos, and branding resources
│   ├── app_icon.ico
│   ├── icon_*.png
│   └── logo_raw.png
├── bolido/                     # Core application package
│   ├── core/                   # Detection engine and algorithms
│   │   ├── backends/           # Execution backends (CUDA GPU and multi-core CPU)
│   │   │   ├── base.py
│   │   │   ├── cpu_backend.py
│   │   │   └── gpu_backend.py
│   │   ├── detector.py         # Transient detection, tracking & spatial filtering
│   │   └── models.py           # Domain models and dataclasses
│   ├── io/                     # Asynchronous I/O and artifact exporters
│   │   ├── reader.py           # Multi-threaded ring-buffer video capture
│   │   └── video_writer.py     # Exporters for Full-Res clips, composites & Excel
│   ├── ui/                     # PySide6 graphical user interface
│   │   ├── widgets/            # Modular UI components (Controls, Viewer, Player, Splash)
│   │   ├── app.py              # Main window & layout orchestration
│   │   ├── styles.py           # Dark Minimal theme stylesheets
│   │   └── worker.py           # Background analysis QThread worker
│   ├── config.py               # Application configuration parameters
│   └── __init__.py             # Package metadata and version definition
├── run.py                      # Application launcher entry point
├── requirements.txt            # Production dependencies
├── LICENSE                     # MIT License
└── README.md                   # Project documentation
```

---

## Installation & Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/shablakovmihail-dev/Bolido.git
cd Bolido
```

### 2. Create and Activate Virtual Environment

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. Install Dependencies

Install the core dependencies:

```bash
pip install -r requirements.txt
```

### 4. Optional: Enable GPU Acceleration (NVIDIA CUDA)

To enable hardware-accelerated detection with NVIDIA GPUs, install PyTorch with CUDA support:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

> **Note:** If PyTorch or CUDA is not detected, Bolido automatically falls back to its optimized multi-threaded CPU backend.

### 5. Launch Application

Run the application using the launcher:

```bash
python run.py
```

---

## Output Artifacts

When an analysis session completes, Bolido generates a structured output directory:

```text
output/<video_name>_analysis/
├── clips/                      # Full-resolution MP4 event video cuts
│   ├── event_001.mp4
│   └── event_002.mp4
├── composites/                 # Max-Merge event composites
│   ├── composite_001.jpg
│   └── composite_002.jpg
├── detections.xlsx             # Complete observation log and trajectory metrics
├── master_composite_raw.jpg    # Raw session composite of all detected events
└── master_composite_annotated.jpg # Annotated master composite with event IDs & paths
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
