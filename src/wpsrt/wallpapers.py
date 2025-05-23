import os
from pathlib import Path
from typing import Iterable, Tuple

import click
import imagehash
from PIL import Image, UnidentifiedImageError, ImageFile


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


def scan_directory(directory: Path) -> Iterable[Tuple[Path, ImageFile.ImageFile]]:
    """Generate a directory list and produce a tuple containing filename and image resolution"""
    for root, _, filenames in os.walk(directory):
        for filename in [Path(os.path.join(root, fname)) for fname in filenames]:
            if filename.is_file():
                try:
                    image = Image.open(filename)
                    yield (filename, image)
                except UnidentifiedImageError:
                    continue


def move_wallpaper(wallpaper: Path, target: Path) -> Path:
    """Move file wallpaper to target location"""
    if not target.parent.exists():
        target.parent.mkdir(parents=True)
    return wallpaper.rename(target)


def sort_wallpapers(mode: str, source: Path, target: Path) -> None:
    click.echo(f"Scanning wallpaper directory {source}...")
    wallpapers = [wallpaper for wallpaper in scan_directory(source)]
    moved_files = []
    with click.progressbar(wallpapers, label="Sorting wallpapers") as progress:
        for filename, image in progress:
            xres, yres = image.size
            if mode == "resolution":
                if filename.is_relative_to(target / f"by-resolution/{xres}x{yres}"):
                    continue
                new_filename = move_wallpaper(
                    filename, target / f"by-resolution/{xres}x{yres}/{filename.name}"
                )
            else:
                ratio = calculate_aspect_ratio(xres, yres)
                if filename.is_relative_to(target / f"by-aspect-ratio/{ratio}"):
                    continue
                new_filename = move_wallpaper(
                    filename, target / f"by-aspect-ratio/{ratio}/{filename.name}"
                )
            moved_files.append(new_filename)

    click.echo(f"Moved {len(moved_files)} file(s).")
    for filename in moved_files:
        click.echo(f"- {filename}")


def hash_wallpapers(target: Path) -> list[tuple[str, str, ImageFile.ImageFile]]:
    click.echo(f"Scanning wallpaper directory {target}...")
    wallpapers = [wallpaper for wallpaper in scan_directory(target)]
    hashes = []
    with click.progressbar(wallpapers, label="Hashing wallpapers") as progress:
        for filename, image in progress:
            phash = imagehash.phash(image)
            hashes.append((filename, phash, image))

    for filename, phash, image in hashes:
        xres, yres = image.size
        print(f"{phash} {xres:6d} {yres:6d} {filename}")

    return hashes
