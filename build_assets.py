#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOLIDO - Asset & Icon Build Script
Generates multi-resolution PNG icons and Windows multi-size .ico from assets/logo_raw.png.
"""

from pathlib import Path
from typing import List, Tuple
from PIL import Image


def generate_icons(
    source_path: Path | str = "assets/logo_raw.png",
    output_dir: Path | str = "assets",
    sizes: List[int] = [256, 64, 32, 16],
) -> List[Path]:
    """
    Downsamples the raw transparent logo to target resolutions and produces
    both PNG files and a multi-resolution Windows .ico file.
    """
    src = Path(source_path).resolve()
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        raise FileNotFoundError(f"Source logo not found at {src}")

    # Open source image in RGBA mode
    img = Image.open(src).convert("RGBA")
    w, h = img.size

    generated_files: List[Path] = []
    resized_images: List[Image.Image] = []

    resample_filter = getattr(Image, "Resampling", Image).LANCZOS

    for size in sizes:
        # Scale proportionally to fit within (size, size) without distortion
        scale = min(size / w, size / h)
        nw = max(1, int(round(w * scale)))
        nh = max(1, int(round(h * scale)))

        scaled = img.resize((nw, nh), resample=resample_filter)

        # Place onto a transparent square canvas centered
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        paste_x = (size - nw) // 2
        paste_y = (size - nh) // 2
        canvas.paste(scaled, (paste_x, paste_y), scaled)

        png_path = out_dir / f"icon_{size}.png"
        canvas.save(png_path, format="PNG")
        generated_files.append(png_path)
        resized_images.append(canvas)
        print(f"Generated {png_path.name} ({size}x{size})")

    # Generate multi-size .ico file for Windows
    ico_path = out_dir / "app_icon.ico"
    # PIL can write multi-size ICO by specifying the sizes tuple list
    ico_sizes: List[Tuple[int, int]] = [(s, s) for s in sizes]
    # The largest icon is base, PIL creates mipmaps for the given sizes
    resized_images[0].save(ico_path, format="ICO", sizes=ico_sizes)
    generated_files.append(ico_path)
    print(f"Generated multi-size {ico_path.name} with resolutions: {sizes}")

    return generated_files


def ensure_assets(project_root: Path | None = None) -> None:
    """Ensures that all required icon assets exist, generating them if missing."""
    if project_root is None:
        project_root = Path(__file__).resolve().parent

    assets_dir = project_root / "assets"
    ico_path = assets_dir / "app_icon.ico"
    raw_logo = assets_dir / "logo_raw.png"

    if raw_logo.exists() and not ico_path.exists():
        generate_icons(source_path=raw_logo, output_dir=assets_dir)


if __name__ == "__main__":
    generate_icons()
