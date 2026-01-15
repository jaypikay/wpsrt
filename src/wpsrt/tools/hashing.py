from pathlib import Path

import click
import imagehash
from PIL import Image

from wpsrt.errors import SkipUnsupportedImage
from wpsrt.wallpapers import scan_directory


def hash_wallpapers(
    target: Path,
) -> list[tuple[Path, imagehash.ImageHash, tuple[int, int]]]:
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
    found_files = list(scan_directory(target))  # Collect all wallpapers first
    hashes: list[tuple[Path, imagehash.ImageHash, tuple[int, int]]] = []
    with click.progressbar(found_files, label="Hashing wallpapers") as progress:
        for filename in progress:
            try:
                image = Image.open(filename)
                phash = imagehash.phash(image)
                hashes.append((filename, phash, image.size))
            except SkipUnsupportedImage:
                click.secho(f"Error hashing {filename}: {e}", err=True, fg="red")
                continue

    # Output the collected hash information
    # This part might be refactored later if actual duplicate removal is implemented
    for filename, phash, image_size in hashes:
        xres, yres = image_size
        # Use click.echo for consistent output formatting
        click.echo(f"{phash} {xres:6d}x{yres:<6d} {filename}")

    return hashes
