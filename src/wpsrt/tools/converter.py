from __future__ import annotations

from pathlib import Path

import click
from PIL import Image, UnidentifiedImageError

from wpsrt.errors import SkipUnsupportedImage
from wpsrt.wallpapers import scan_directory


def convert_wallpapers(extension: str, remove_original: bool, source: Path) -> None:
    """Converts images matching the given extension to PNG format."""
    click.echo(f"Scanning wallpaper directory {source}...")
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
            except (UnidentifiedImageError, SkipUnsupportedImage):
                continue

    click.echo(f"Converted {len(converted_files)} file(s).")
    for filename in converted_files:
        click.echo(f"- {filename}")
