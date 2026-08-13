from __future__ import annotations

import math
from pathlib import Path

import click
from PIL import Image, UnidentifiedImageError

from wpsrt.errors import SkipUnsupportedImage

FOLDER_PREFIX = "by-ratio"


def calculate_aspect_ratio(width: int, height: int) -> str:
    """Calculates the aspect ratio of an image given its width and height.

    The aspect ratio is simplified by dividing both width and height by their
    greatest common divisor (GCD).

    Args:
        width: The width of the image in pixels.
        height: The height of the image in pixels.

    Returns:
        A string representing the simplified aspect ratio in 'W:H' format
        (e.g., '16:9', '4:3').
    """
    divisor = math.gcd(width, height)
    simplified_width = width // divisor
    simplified_height = height // divisor
    return f"{simplified_width}:{simplified_height}"


def process_file(filename: Path) -> Path:
    try:
        with Image.open(filename) as image:
            xres, yres = image.size
        ratio = calculate_aspect_ratio(xres, yres)
        return Path(f"{FOLDER_PREFIX}/{ratio}/{filename.name}")
    except UnidentifiedImageError:
        click.secho(
            f"WARN: Skipping unsupported file: {filename}", fg="yellow", err=True
        )
        raise SkipUnsupportedImage from None
