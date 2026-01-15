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
from typing import Generator

import click

from wpsrt.errors import SkipUnsupportedImage, UnknownSortMethod
from wpsrt.methods import aspectratio, resolution, nsfw


def scan_directory(directory: Path) -> Generator[Path]:
    for root, _, filenames in os.walk(directory):
        for filename in [Path(os.path.join(root, fname)) for fname in filenames]:
            if filename.is_file():
                yield filename


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
    found_files = list(scan_directory(source))  # Collect all wallpapers first
    moved_files = 0
    skipped_files = 0
    sfw_files = 0
    nsfw_files = 0

    with click.progressbar(found_files, label="Sorting wallpapers") as progress:
        for filename in progress:
            try:
                match mode:
                    case "resolution":
                        fname = resolution.process_file(filename)
                    case "ratio":
                        fname = aspectratio.process_file(filename)
                    case "nsfw":
                        fname = nsfw.process_file(filename)
                        if "/NSFW/" in fname.as_posix():
                            nsfw_files += 1
                        else:
                            sfw_files += 1
                    case _:
                        click.secho(
                            "WARN: Unknown sorting method specified.",
                            fg="yellow",
                            err=True,
                        )
                        raise UnknownSortMethod

                target_subdir_fname = target / fname
                new_filename = move_wallpaper(filename, target_subdir_fname)
                moved_files += 1
            except SkipUnsupportedImage:
                skipped_files += 1
                continue

    click.echo(f"\nSummary\n{'=' * 25}")
    click.echo(f"- Moved {moved_files:>8} file(s).")
    click.echo(f"- Skipped {skipped_files:>6} file(s).")
    if mode == "nsfw":
        click.echo("-" * 25)
        click.echo(f"- NSFW {nsfw_files:>9} file(s).")
        click.echo(f"- SFW {sfw_files:>10} file(s).")
