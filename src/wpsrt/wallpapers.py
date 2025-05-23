import os
from pathlib import Path
from typing import Iterable, Tuple

from PIL import Image, UnidentifiedImageError


def calculate_aspect_ratio(width: int, height: int) -> str:
    """
    Calculate the aspect ratio from width and height.
    Returns the ratio in the format 'width:height' (e.g., '16:9', '4:3', etc.)
    """

    # Calculate the greatest common divisor (GCD)
    def gcd(a, b):
        while b:
            a, b = b, a % b
        return a

    # Find the GCD of width and height
    divisor = gcd(width, height)

    # Simplify the ratio
    simplified_width = width // divisor
    simplified_height = height // divisor

    # Return the ratio as a string
    return f"{simplified_width}:{simplified_height}"


def scan_directory(directory: Path) -> Iterable[Tuple[Path, Tuple[int, int]]]:
    """Generate a directory list and produce a tuple containing filename and image resolution"""
    for root, _, filenames in os.walk(directory):
        for filename in [Path(os.path.join(root, fname)) for fname in filenames]:
            if filename.is_file():
                try:
                    image = Image.open(filename)
                    yield (filename, image.size)
                except UnidentifiedImageError:
                    continue


def move_wallpaper(wallpaper: Path, target: Path) -> Path:
    """Move file wallpaper to target location"""
    if not target.parent.exists():
        target.parent.mkdir(parents=True)
    return wallpaper.rename(target)
