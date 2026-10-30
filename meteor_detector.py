#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI entry point for BOLIDO - Offline Computer Vision Night Sky Video Analyzer.
Uses modular bolido core engine with hardware acceleration.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List

from bolido.config import DetectionConfig, DeviceConfig, DeviceType
from bolido.core.detector import MeteorDetector
from bolido.core.models import CandidateDetection, MeteorEvent
from bolido.io.video_writer import safe_imwrite


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Meteor Detector (BOLIDO) - Offline Computer Vision Night Sky Video Analyzer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="Path to an input video file (.mp4, .mkv, .avi, .mov) or directory of videos",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="./output",
        help="Root directory where detection results will be saved",
    )
    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=35.0,
        help="Sensitivity threshold for frame differencing (typical: 25-50)",
    )
    parser.add_argument(
        "-l", "--min-length",
        type=float,
        default=15.0,
        help="Minimum required meteor track length in pixels",
    )
    parser.add_argument(
        "--buffer-sec",
        type=float,
        default=1.5,
        help="Buffer duration (in seconds) to retain before and after each meteor event clip",
    )
    parser.add_argument(
        "--min-frames",
        type=int,
        default=2,
        help="Minimum duration of an event in frames (filters single-frame glitches & plane strobes)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=25,
        help="Maximum duration of an event in frames (filters satellites & aircraft)",
    )
    parser.add_argument(
        "--device",
        type=str,
        choices=["auto", "cuda", "cpu"],
        default="auto",
        help="Hardware compute backend",
    )
    parser.add_argument(
        "--downscale",
        type=int,
        default=1280,
        help="Screening target width in pixels (0 = native resolution)",
    )
    parser.add_argument(
        "--no-clean-image",
        action="store_true",
        help="Disable saving pristine unannotated max-merge JPEG files",
    )

    return parser.parse_args()


def collect_video_files(input_path: Path) -> List[Path]:
    valid_extensions = {".mp4", ".mkv", ".avi", ".mov", ".m4v"}
    if input_path.is_file():
        if input_path.suffix.lower() in valid_extensions:
            return [input_path]
        raise ValueError(f"Unsupported video format: {input_path.suffix}")

    if input_path.is_dir():
        files = [p for p in input_path.iterdir() if p.is_file() and p.suffix.lower() in valid_extensions]
        files.sort()
        return files

    raise FileNotFoundError(f"Provided path does not exist: {input_path}")


def print_summary_table(all_detections: Dict[str, List[MeteorEvent]]):
    total_events = sum(len(evs) for evs in all_detections.values())
    print("\n" + "=" * 76)
    print("                    METEOR DETECTION SUMMARY")
    print("=" * 76)
    print(f"{'Video File':<24} | {'Event ID':<8} | {'Time (sec)':<14} | {'Frames':<8} | {'Length (px)':<10}")
    print("-" * 76)

    if total_events == 0:
        print(" No meteors detected in the analyzed video(s).")
    else:
        for video_name, events in all_detections.items():
            for ev in events:
                time_str = f"{ev.start_time_sec:.2f} - {ev.end_time_sec:.2f}"
                print(
                    f"{video_name:<24} | "
                    f"#{ev.event_id:<7} | "
                    f"{time_str:<14} | "
                    f"{ev.duration_frames:<8} | "
                    f"{ev.approx_length_px:<10.1f}"
                )

    print("=" * 76)
    print(f"Total video(s) processed: {len(all_detections)} | Total meteor(s) identified: {total_events}\n")


def main():
    args = parse_args()
    input_path = Path(args.input)
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    video_files = collect_video_files(input_path)
    if not video_files:
        print(f"[ERROR] No compatible video files found at: {input_path}")
        sys.exit(1)

    print(f"\n=======================================================")
    print(f"   BOLIDO: Offline Meteor Detector & Video Analyzer    ")
    print(f"=======================================================")
    print(f"Total files to process: {len(video_files)}")
    print(f"Output directory:       {output_root.resolve()}\n")

    dev_type = DeviceType(args.device)
    dev_config = DeviceConfig(
        device_type=dev_type,
        target_width=args.downscale,
    )
    config = DetectionConfig(
        threshold=args.threshold,
        min_length=args.min_length,
        buffer_sec=args.buffer_sec,
        min_frames=args.min_frames,
        max_frames=args.max_frames,
        save_clean=not args.no_clean_image,
        device=dev_config,
    )

    detector = MeteorDetector(config=config)
    all_detections: Dict[str, List[MeteorEvent]] = {}
    t_start = time.time()

    for video_file in video_files:
        events = detector.process_video(video_file, output_root)
        all_detections[video_file.name] = events

    elapsed = time.time() - t_start
    print_summary_table(all_detections)
    print(f"[FINISHED] Completed batch analysis in {elapsed:.2f} seconds.")


if __name__ == "__main__":
    main()
