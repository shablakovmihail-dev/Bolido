#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOLIDO - Asset Path Utilities
"""

import sys
from pathlib import Path


def get_asset_path(filename: str) -> Path:
    """
    Resolves the path to a file inside the assets directory.
    Checks PyInstaller bundle (_MEIPASS), executable dir, cwd, and package root.
    """
    # 1. PyInstaller temporary unpack directory (_internal / bundle root)
    if hasattr(sys, "_MEIPASS"):
        meipass_candidate = Path(sys._MEIPASS) / "assets" / filename
        if meipass_candidate.exists():
            return meipass_candidate

    # 2. Alongside standalone executable (or _internal)
    if getattr(sys, "frozen", False):
        exe_candidate = Path(sys.executable).resolve().parent / "assets" / filename
        if exe_candidate.exists():
            return exe_candidate
        internal_candidate = Path(sys.executable).resolve().parent / "_internal" / "assets" / filename
        if internal_candidate.exists():
            return internal_candidate

    # 3. Current working directory
    cwd_candidate = Path("assets") / filename
    if cwd_candidate.exists():
        return cwd_candidate

    # 4. Relative to this file: bolido/ui/assets.py -> project root / assets
    package_root = Path(__file__).resolve().parent.parent.parent
    root_candidate = package_root / "assets" / filename
    if root_candidate.exists():
        return root_candidate

    return cwd_candidate
