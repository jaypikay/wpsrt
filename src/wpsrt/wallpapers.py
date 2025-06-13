"""
This module provides core functionalities for wallpaper sorting and management.

It includes functions to:
- Calculate aspect ratios of images.
- Scan directories for image files.
- Move wallpaper files to specified locations.
- Sort wallpapers into subdirectories based on resolution or aspect ratio.
- Identify duplicate images by calculating and comparing perceptual hashes.
"""
import os
from pathlib import Path
from typing import Iterable, Tuple

import click
import imagehash
from PIL import Image, UnidentifiedImageError, ImageFile


def calculate_aspect_ratio(width: int, height: int) -> str:
    """
    Calculates the aspect ratio of an image given its width and height.

    The aspect ratio is simplified by dividing both width and height by their
    greatest common divisor (GCD).

    Args:
        width: The width of the image in pixels.
        height: The height of the image in pixels.

    Returns:
        A string representing the simplified aspect ratio in 'W:H' format
        (e.g., '16:9', '4:3').
    """

    def gcd(a, b):
        """Computes the greatest common divisor of two integers."""
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
    """
    Scans a directory for image files and yields their paths and PIL Image objects.

    This function recursively walks through the given directory. For each file found,
    it attempts to open it as an image. If successful, it yields a tuple
    containing the file's Path object and the PIL ImageFile.ImageFile object.
    It skips files that cannot be identified as images by PIL.

    Args:
        directory: The Path object representing the directory to scan.

    Yields:
        An iterable of tuples, where each tuple contains:
            - filename (Path): The path to an image file.
            - image (ImageFile.ImageFile): The PIL Image object for the image file.
    """
    for root, _, filenames in os.walk(directory):
        for filename in [Path(os.path.join(root, fname)) for fname in filenames]:
            if filename.is_file():
                try:
                    image = Image.open(filename)
                    yield (filename, image)
                except UnidentifiedImageError:
                    # Skip files that are not recognized as images
                    click.echo(f"Skipping non-image file: {filename}", err=True)
                    continue


def move_wallpaper(wallpaper: Path, target: Path) -> Path:
    """
    Moves a wallpaper file to a specified target path.

    If the parent directory of the target path does not exist, it will be
    created recursively.

    Args:
        wallpaper: The Path object of the wallpaper file to move.
        target: The Path object representing the destination path for the wallpaper.

    Returns:
        The Path object of the moved wallpaper file at its new location.
    """
    if not target.parent.exists():
        # Create parent directories if they don't exist
        target.parent.mkdir(parents=True)
    return wallpaper.rename(target)


def sort_wallpapers(mode: str, source: Path, target: Path) -> None:
    """
    Sorts wallpapers from a source directory into subdirectories within a target directory.

    Wallpapers can be sorted based on their resolution or aspect ratio.
    It skips files that are already in their correct target subdirectories.

    Args:
        mode: The sorting criterion, either "resolution" or "ratio".
        source: The Path object of the directory containing wallpapers to sort.
        target: The Path object of the directory where sorted wallpapers will be placed.
                Subdirectories will be created here based on the sorting mode.
    """
    click.echo(f"Scanning wallpaper directory {source}...")
    wallpapers = list(scan_directory(source)) # Collect all wallpapers first
    moved_files = []
    with click.progressbar(wallpapers, label="Sorting wallpapers") as progress:
        for filename, image in progress:
            xres, yres = image.size
            if mode == "resolution":
                target_subdir = target / f"by-resolution/{xres}x{yres}"
                # Skip if file is already in the correct target subdirectory
                if filename.is_relative_to(target_subdir):
                    continue
                new_filename = move_wallpaper(
                    filename, target_subdir / filename.name
                )
            elif mode == "ratio": # Added elif for clarity, though 'else' would also work
                ratio = calculate_aspect_ratio(xres, yres)
                target_subdir = target / f"by-aspect-ratio/{ratio}"
                # Skip if file is already in the correct target subdirectory
                if filename.is_relative_to(target_subdir):
                    continue
                new_filename = move_wallpaper(
                    filename, target_subdir / filename.name
                )
            else:
                # Should not happen due to click.Choice in main.py, but good for robustness
                click.echo(f"Unknown sort mode: {mode}", err=True, color="red")
                continue
            moved_files.append(new_filename)

    click.echo(f"Moved {len(moved_files)} file(s).")
    for filename in moved_files:
        click.echo(f"- {filename}")


def hash_wallpapers(target: Path) -> list[tuple[Path, imagehash.ImageHash, ImageFile.ImageFile]]:
    """
    Scans a directory for images, calculates their perceptual hashes (phash),
    and prints this information.

    This function is useful for identifying potential duplicate images by comparing
    their hash values. It prints the phash, resolution (formatted as 'WIDTHxHEIGHT'),
    and filename for each image. Example: `d8e8c0c0c0c0e0e0 1920x1080 /path/to/image.jpg`

    Args:
        target: The Path object of the directory to scan for wallpapers.

    Returns:
        A list of tuples, where each tuple contains:
            - filename (Path): The path to the image file.
            - phash (imagehash.ImageHash): The perceptual hash of the image.
            - image (ImageFile.ImageFile): The PIL Image object.
    """
    click.echo(f"Scanning wallpaper directory {target} for hashing...")
    wallpapers = list(scan_directory(target)) # Collect all wallpapers first
    hashes: list[tuple[Path, imagehash.ImageHash, ImageFile.ImageFile]] = []
    with click.progressbar(wallpapers, label="Hashing wallpapers") as progress:
        for filename, image in progress:
            try:
                phash = imagehash.phash(image)
                hashes.append((filename, phash, image))
            except Exception as e:
                click.echo(f"Error hashing {filename}: {e}", err=True, color="red")
                continue

    # Output the collected hash information
    # This part might be refactored later if actual duplicate removal is implemented
    for filename, phash, image in hashes:
        xres, yres = image.size
        # Use click.echo for consistent output formatting
        click.echo(f"{phash} {xres:6d}x{yres:<6d} {filename}")

    return hashes
