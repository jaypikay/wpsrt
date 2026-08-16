"""
A command-line tool for sorting wallpapers based on various criteria.

This script allows users to organize their wallpaper collections by sorting
images into subdirectories based on their resolution, aspect ratio, or by
removing duplicates based on their hash.
"""

from __future__ import annotations

import logging
from pathlib import Path

import click

from wpsrt.tools.log import setup_logging

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "-m",
    "--mode",
    type=click.Choice(["resolution", "ratio", "nsfw", "clip"]),
    default="resolution",
    help="Sort by resolution, aspect ratio, NSFW rating, or CLIP category.",
)
@click.option(
    "-n",
    "--nsfw-model",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Custom ONNX model path for NSFW detection.",
)
@click.option("-d", "--dry-run", is_flag=True, help="Do not perform any file actions.")
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
def wpsort(
    mode: str, nsfw_model: Path | None, dry_run: bool, source: Path, target: Path
) -> None:
    """Sorts wallpapers from a source directory to a target directory.

    The sorting can be done based on different modes:

    - 'resolution': Sorts wallpapers into subdirectories named after their resolution (e.g., '1920x1080').

    - 'ratio': Sorts wallpapers into subdirectories named after their aspect ratio (e.g., '16:9').

    - 'nsfw': Sorts wallpapers by SFW / NSFW content.

    - 'clip': Sorts wallpapers into category subdirectories using CLIP.
    """
    setup_logging()
    source = Path(source)
    target = Path(target)
    logger.info(
        "wpsort invoked: mode=%s source=%s target=%s dry_run=%s",
        mode,
        source,
        target,
        dry_run,
    )
    if not target.exists() and not dry_run:
        target.mkdir(parents=True, exist_ok=True)

    if nsfw_model:
        from wpsrt.methods.nsfw import reinitialize_detector

        reinitialize_detector(nsfw_model)

    if mode in ["resolution", "ratio", "nsfw", "clip"]:
        from .wallpapers import sort_wallpapers

        sort_wallpapers(mode, source, target, dry_run)


@click.command()
@click.option(
    "-m",
    "--mode",
    type=click.Choice(["clean", "hash", "compare"]),
    default="hash",
    help="Operational mode selection",
)
@click.option(
    "-h",
    "--hash",
    "hash_method",
    type=click.Choice(["phash", "dhash", "colorhash", "average_hash"]),
    default="dhash",
    help="Hash used for comparison during similarity check",
)
@click.option(
    "-t",
    "--threshold",
    type=int,
    default=5,
    help="Threshold distance during similarity check",
)
@click.option(
    "-o",
    "--output",
    default=None,
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    help="Output file for similarity results",
)
@click.argument(
    "target",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=Path("~/Pictures/Wallpapers/").expanduser(),
)
def wphash(
    target: Path, mode: str, hash_method: str, threshold: int, output: Path | None
) -> None:
    """Hash, compare and clean image hashes.

    Example usage:

        wphash -m compare | swiv -t -i

        wphash -m compare -o similarities.dhash
    """
    setup_logging()
    target = Path(target)
    logger.info(
        "wphash invoked: mode=%s hash_method=%s threshold=%s target=%s",
        mode,
        hash_method,
        threshold,
        target,
    )
    if mode == "hash":
        from .tools.hashing import hash_wallpapers

        hash_wallpapers(target)

    if mode == "compare":
        from .tools.hashing import compare_hashes

        out_path = Path(output) if output else None
        compare_hashes(hash_method, threshold, out_path)

    if mode == "clean":
        from .tools.hashing import cleanup_hashes

        cleanup_hashes()


@click.command()
@click.option(
    "-e", "--extension", type=str, default="webp", help="Convert of type EXT to png"
)
@click.option(
    "-d",
    "--delete",
    is_flag=True,
    default=False,
    help="Remove original file after conversion",
)
@click.argument(
    "source",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=Path("~/Pictures/wallpapers").expanduser(),
)
def wpconvert(extension: str, delete: bool, source: Path) -> None:
    """Convert images with specific extension to PNG."""
    setup_logging()
    source = Path(source)
    logger.info(
        "wpsrt-convert invoked: extension=%s delete=%s source=%s",
        extension,
        delete,
        source,
    )

    if extension.lower().strip(".") == "gif":
        click.secho("Cannot convert gif to png!", fg="red")
        logger.warning("Refused to convert gif to png for source=%s", source)
        return

    from .tools.converter import convert_wallpapers

    convert_wallpapers(extension, delete, source)
