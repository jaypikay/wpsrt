from pathlib import Path

import click
from PIL import Image

from wpsrt.errors import SkipUnsupportedImage
from wpsrt.wallpapers import scan_directory


def convert_wallpapers(extension: str, remove_original: bool, source: Path):
    click.echo(f"Scanning wallpaper directory {source}...")
    converted_files = []
    for filename, _ in scan_directory(source):
        if filename.as_posix().endswith(f".{extension}"):
            try:
                image = Image.open(filename)
                new_filename = filename.with_suffix(".png")
                if not new_filename.exists():
                    click.echo(f"- Converting {filename.name} to PNG...")
                    image.save(new_filename)
                    if remove_original:
                        filename.unlink()
                    converted_files.append(filename)
                image.close()
            except SkipUnsupportedImage:
                continue
    click.echo(f"Converted {len(converted_files)} file(s).")
    for filename in converted_files:
        click.echo(f"- {filename}")
