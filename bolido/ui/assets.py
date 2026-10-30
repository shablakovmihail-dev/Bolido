#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOLIDO - Asset Path Utilities
"""

from pathlib import Path


def get_asset_path(filename: str) -> Path:
    """
    Resolves the path to a file inside the assets directory.
    Checks relative to current working directory first, then package root.
    """
    cwd_candidate = Path("assets") / filename
    if cwd_candidate.exists():
        return cwd_candidate

    # Relative to this file: bolido/ui/assets.py -> project root / assets
    package_root = Path(__file__).resolve().parent.parent.parent
    root_candidate = package_root / "assets" / filename
    if root_candidate.exists():
        return root_candidate

    return cwd_candidate
