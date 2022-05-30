import os
from pathlib import Path
from typing import Iterable, Tuple

from PIL import Image


def scan_directory(directory: Path) -> Iterable[Tuple[Path, Tuple[int, int]]]:
    for root, _, filenames in os.walk(directory):
        for filename in [Path(os.path.join(root, fname)) for fname in filenames]:
            if filename.is_file():
                image = Image.open(filename)
                yield (filename, image.size)


def move_wallpaper(wallpaper: Path, target: Path) -> Path:
    if not target.parent.exists():
        target.parent.mkdir()
    return wallpaper.rename(target)
