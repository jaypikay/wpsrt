from __future__ import annotations

import logging
from pathlib import Path

import click
from PIL import Image, UnidentifiedImageError

from wpsrt.errors import SkipUnsupportedImage
from wpsrt.wallpapers import scan_directory

logger = logging.getLogger(__name__)


def convert_wallpapers(extension: str, remove_original: bool, source: Path) -> None:
    """Converts images matching the given extension to PNG format."""
    click.echo(f"Scanning wallpaper directory {source}...")
    logger.info(
        "Converting %s files in %s (remove_original=%s)",
        extension,
        source,
        remove_original,
    )
    converted_files: list[Path] = []
    target_ext = f".{extension.lower().lstrip('.')}"

    for filename in scan_directory(source):
        if filename.suffix.lower() == target_ext:
            try:
                new_filename = filename.with_suffix(".png")
                if not new_filename.exists():
                    click.echo(f"- Converting {filename.name} to PNG...")
                    with Image.open(filename) as image:
                        image.save(new_filename)
                    if remove_original:
                        filename.unlink()
                    converted_files.append(filename)
            except (UnidentifiedImageError, SkipUnsupportedImage) as ex:
                logger.warning("Skipping %s: %s", filename, ex)
                continue

    click.echo(f"Converted {len(converted_files)} file(s).")
    logger.info("Converted %d file(s)", len(converted_files))
    for filename in converted_files:
        click.echo(f"- {filename}")