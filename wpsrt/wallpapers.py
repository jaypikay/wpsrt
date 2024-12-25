import os
from pathlib import Path
from typing import Iterable, Tuple

from enlighten import get_manager
from PIL import Image, UnidentifiedImageError


def scan_directory(directory: Path) -> Iterable[Tuple[Path, Tuple[int, int]]]:
    with get_manager() as manager:
        manager.status_bar("Sorting Wallpapers...", color="white_on_blue")
        with manager.counter(desc="Sorting", unit="images") as pbar:
            for root, _, filenames in os.walk(directory):
                for filename in [
                    Path(os.path.join(root, fname)) for fname in filenames
                ]:
                    if filename.is_file():
                        try:
                            image = Image.open(filename)
                            yield (filename, image.size)
                        except UnidentifiedImageError:
                            continue
                    pbar.update()


def move_wallpaper(wallpaper: Path, target: Path) -> Path:
    if not target.parent.exists():
        target.parent.mkdir()
    return wallpaper.rename(target)
