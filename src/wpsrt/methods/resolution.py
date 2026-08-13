from __future__ import annotations

from pathlib import Path

import click
from PIL import Image, UnidentifiedImageError

from wpsrt.errors import SkipUnsupportedImage

FOLDER_PREFIX = "by-resolution"


def process_file(filename: Path) -> Path:
    """Processes an image file and returns its target path based on resolution."""
    try:
        with Image.open(filename) as image:
            xres, yres = image.size
        return Path(f"{FOLDER_PREFIX}/{xres}x{yres}/{filename.name}")
    except UnidentifiedImageError:
        click.secho(
            f"WARN: Skipping unsupported file: {filename}", fg="yellow", err=True
        )
        raise SkipUnsupportedImage from None
