from pathlib import Path

import click
from PIL import Image, UnidentifiedImageError

from wpsrt.errors import SkipUnsupportedImage

FOLDER_PREFIX = "by-resolution"


def process_file(filename: Path) -> Path:
    try:
        image = Image.open(filename)
        xres, yres = image.size
        return Path(f"{FOLDER_PREFIX}/{xres}x{yres}/{filename.name}")
    except UnidentifiedImageError:
        click.secho(
            f"WARN: Skipping unsupported file: {filename}", fg="yellow", err=True
        )
        raise SkipUnsupportedImage
