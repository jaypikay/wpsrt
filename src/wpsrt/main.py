"""
A command-line tool for sorting wallpapers based on various criteria.

This script allows users to organize their wallpaper collections by sorting
images into subdirectories based on their resolution, aspect ratio, or by
removing duplicates based on their hash.
"""
from pathlib import Path

import click

from .wallpapers import sort_wallpapers, hash_wallpapers


@click.command()
@click.option(
    "-m",
    "--mode",
    type=click.Choice(["resolution", "ratio", "hash"]),
    default="resolution",
    help="Sort by resolution or aspect ratio.",
)
@click.argument(
    "source",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=Path("~/Pictures/wallpapers").expanduser(),
)
@click.argument(
    "target",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
    default=Path("~/Pictures/wallpapers").expanduser(),
)
def wpsort(mode: str, source: Path, target: Path) -> None:
    """
    Sorts wallpapers from a source directory to a target directory.

    The sorting can be done based on different modes:
    - 'resolution': Sorts wallpapers into subdirectories named after their resolution (e.g., '1920x1080').
    - 'ratio': Sorts wallpapers into subdirectories named after their aspect ratio (e.g., '16x9').
    - 'hash': Calculates and displays perceptual hashes of wallpapers in the target directory.
              (Note: This mode currently only identifies potential duplicates by hash, it does not remove them).

    Args:
        mode: The sorting mode to use ('resolution', 'ratio', or 'hash').
        source: The path to the directory containing the wallpapers to sort.
        target: The path to the directory where the sorted wallpapers will be placed.
                If it doesn't exist, it will be created.
    """
    source = Path(source)
    target = Path(target)
    if not target.exists():
        target.mkdir(parents=True)

    if mode in ["resolution", "ratio"]:
        sort_wallpapers(mode, source, target)
    elif mode in ["hash"]:
        hash_wallpapers(target)
