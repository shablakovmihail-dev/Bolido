#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
BOLIDO - Web-UI (Streamlit)
================================================================================
Browser-based interface for offline meteor detection and night sky analysis.
Run with: streamlit run app.py
================================================================================
"""

import io
import os
import shutil
import time
import zipfile
from pathlib import Path
from typing import Dict, List

import cv2
import pandas as pd
import streamlit as st

from meteor_detector import MeteorDetector, MeteorEvent, collect_video_files

# Page configuration
st.set_page_config(
    page_title="BOLIDO — Meteor Detector",
    page_icon="assets/icon_32.png" if Path("assets/icon_32.png").exists() else "☄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Astro Dark Theme CSS
st.markdown(
    """
    <style>
    /* Dark Astro Theme Tweaks */
    .stApp {
        background-color: #0A0D14;
        color: #E2E8F0;
    }
    .metric-card {
        background-color: #111722;
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .metric-val {
        font-size: 24px;
        font-weight: 800;
        color: #00E673;
    }
    .metric-title {
        font-size: 11px;
        color: #64748B;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .event-card {
        background-color: #111722;
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Sidebar / Controls
# ----------------------------------------------------------------------------
st.sidebar.title("☄️ BOLIDO")
st.sidebar.caption("Offline Night Sky Meteor & Fireball Detector")

st.sidebar.markdown("---")
st.sidebar.subheader("Input Source")

source_type = st.sidebar.radio("Mode", ["Single Video File", "Folder of Videos"], index=0)

default_input = "test_night_sky.mp4" if Path("test_night_sky.mp4").exists() else ""
input_path_str = st.sidebar.text_input(
    "Video or Directory Path",
    value=default_input,
    help="Enter local path to video file (.mp4, .mkv, .avi) or folder",
)

output_dir_str = st.sidebar.text_input("Output Directory", value="./output")

st.sidebar.markdown("---")
st.sidebar.subheader("Detection Parameters")

threshold = st.sidebar.slider(
    "Sensitivity Threshold", min_value=10.0, max_value=100.0, value=35.0, step=1.0,
    help="Brightness difference required above background. Lower = more sensitive.",
)

min_length = st.sidebar.slider(
    "Min Track Length (px)", min_value=5.0, max_value=60.0, value=15.0, step=1.0,
    help="Minimum required streak / trajectory displacement in pixels.",
)

buffer_sec = st.sidebar.slider(
    "Buffer Window (seconds)", min_value=0.5, max_value=3.0, value=1.5, step=0.1,
    help="Duration of pre- and post-event context included in generated MP4 clips.",
)

learning_rate = st.sidebar.slider(
    "Background Learning Rate (alpha)", min_value=0.01, max_value=0.15, value=0.05, step=0.01,
)

start_clicked = st.sidebar.button("🚀 Start Analysis", type="primary", use_container_width=True)

# ----------------------------------------------------------------------------
# Main Dashboard
# ----------------------------------------------------------------------------
st.title("Night Sky Analysis Dashboard")

if "results" not in st.session_state:
    st.session_state.results = {}
if "analysis_time" not in st.session_state:
    st.session_state.analysis_time = 0.0

if start_clicked:
    if not input_path_str.strip():
        st.error("Please enter a valid video file or directory path.")
    else:
        input_path = Path(input_path_str.strip())
        output_dir = Path(output_dir_str.strip() or "./output")
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            video_files = collect_video_files(input_path)
        except Exception as e:
            st.error(f"Error reading path: {e}")
            video_files = []

        if not video_files:
            st.warning("No compatible video files found at the specified path.")
        else:
            progress_bar = st.progress(0, text="Initializing detector...")
            fps_metric = st.empty()

            detector = MeteorDetector(
                threshold=threshold,
                min_length=min_length,
                buffer_sec=buffer_sec,
                learning_rate=learning_rate,
                show_preview=False,
                save_clean=True,
            )

            all_results: Dict[str, List[MeteorEvent]] = {}
            t0 = time.time()

            for vid_idx, vid_file in enumerate(video_files, start=1):
                def progress_cb(cur_f, tot_f, cur_fps):
                    pct = cur_f / tot_f if tot_f > 0 else 0.0
                    progress_bar.progress(
                        pct,
                        text=f"Analyzing {vid_file.name} ({vid_idx}/{len(video_files)}): frame {cur_f}/{tot_f} ({int(pct*100)}%)",
                    )
                    fps_metric.caption(f"⚡ Processing Speed: **{cur_fps:.1f} FPS**")

                events = detector.process_video(
                    video_path=vid_file,
                    output_dir=output_dir,
                    progress_callback=progress_cb,
                )
                all_results[vid_file.name] = events

            progress_bar.progress(1.0, text="Analysis complete!")
            st.session_state.results = all_results
            st.session_state.analysis_time = time.time() - t0
            st.success(f"Analysis finished in {st.session_state.analysis_time:.2f} seconds!")

# ----------------------------------------------------------------------------
# Display Results
# ----------------------------------------------------------------------------
if st.session_state.results:
    total_meteors = sum(len(evs) for evs in st.session_state.results.values())

    # Summary Metrics Row
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"""<div class="metric-card"><div class="metric-title">TOTAL METEORS FOUND</div><div class="metric-val">{total_meteors}</div></div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""<div class="metric-card"><div class="metric-title">VIDEOS ANALYZED</div><div class="metric-val" style="color: #38BDF8;">{len(st.session_state.results)}</div></div>""",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""<div class="metric-card"><div class="metric-title">TOTAL RUNTIME</div><div class="metric-val" style="color: #FBBF24;">{st.session_state.analysis_time:.2f} s</div></div>""",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Detailed Video & Event View
    for video_name, events in st.session_state.results.items():
        st.subheader(f"📹 {video_name} ({len(events)} events)")

        if not events:
            st.info("No meteors detected in this video.")
            continue

        # Event Tabs
        event_tabs = st.tabs([f"☄️ Meteor #{ev.event_id}" for ev in events])

        for tab, ev in zip(event_tabs, events):
            with tab:
                col_img, col_vid = st.columns([1, 1])

                with col_img:
                    st.markdown("#### Max-Pixel Merge Track")
                    img_path = ev.max_merge_path or ev.clean_merge_path
                    if img_path and Path(img_path).exists():
                        st.image(img_path, caption=f"Event #{ev.event_id} - Full Track", use_container_width=True)
                    else:
                        st.info("Composite image not available.")

                with col_vid:
                    st.markdown("#### Event Video Clip (Buffered)")
                    if ev.clip_path and Path(ev.clip_path).exists():
                        st.video(ev.clip_path)
                    else:
                        st.info("Clip not available.")

                # Metadata card
                st.markdown(
                    f"""
                    **Timing:** `{ev.start_time_sec:.2f}s` to `{ev.end_time_sec:.2f}s` | 
                    **Duration:** `{ev.duration_frames} frames` | 
                    **Track Length:** `{ev.approx_length_px:.1f} px` | 
                    **Frames:** `{ev.start_frame}..{ev.end_frame}`
                    """
                )

    # ------------------------------------------------------------------------
    # Export Section
    # ------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📦 Export Results")

    out_dir = Path(output_dir_str.strip() or "./output")
    csv_files = list(out_dir.rglob("detections.csv"))

    col_e1, col_e2 = st.columns(2)

    with col_e1:
        if csv_files:
            with open(csv_files[0], "rb") as f:
                st.download_button(
                    label="📄 Download detections.csv",
                    data=f.read(),
                    file_name="detections.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

    with col_e2:
        # Create ZIP in-memory
        if out_dir.exists():
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for f_path in out_dir.rglob("*"):
                    if f_path.is_file() and not f_path.name.endswith(".zip"):
                        zf.write(f_path, f_path.relative_to(out_dir))
            zip_buffer.seek(0)

            st.download_button(
                label="📦 Download All (ZIP Archive)",
                data=zip_buffer,
                file_name="bolido_detections.zip",
                mime="application/zip",
                use_container_width=True,
            )
else:
    st.info("👈 Select an input video file or folder in the sidebar and click **Start Analysis**.")
