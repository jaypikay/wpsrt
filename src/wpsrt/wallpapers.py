import os
from pathlib import Path
from typing import Iterable, Tuple

from PIL import Image, UnidentifiedImageError


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
        target.parent.mkdir()
    return wallpaper.rename(target)
