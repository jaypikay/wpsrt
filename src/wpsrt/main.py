"""
A command-line tool for sorting wallpapers based on various criteria.

This script allows users to organize their wallpaper collections by sorting
images into subdirectories based on their resolution, aspect ratio, or by
removing duplicates based on their hash.
"""

from pathlib import Path

import click


@click.command()
@click.option(
    "-m",
    "--mode",
    type=click.Choice(["resolution", "ratio", "nsfw", "clip"]),
    default="resolution",
    help="Sort by resolution or aspect ratio.",
)
@click.option(
    "-n",
    "--nsfw-model",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default=None,
)
@click.option("-d", "--dry-run", is_flag=True, help="Do not perform any file actions")
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
    mode: str, nsfw_model: Path, dry_run: bool, source: Path, target: Path
) -> None:
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
    target: The path to the directory where the sorted wallpapers will be placed. If it doesn't exist, it will be created.
    """
    source = Path(source)
    target = Path(target)
    if not target.exists() and not dry_run:
        target.mkdir(parents=True)

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
def wphash(target: Path, mode: str, hash: str, threshold: int, output: Path):
    """Hash, compare and clean image hashes.

    Example usage:

        wphash -m compare | swiv -t -i

        wphash -m compare -o similarities.dhash
    """
    if mode == "hash":
        from .tools.hashing import hash_wallpapers

        hash_wallpapers(Path(target))

    if mode == "compare":
        from .tools.hashing import compare_hashes

        compare_hashes(hash, threshold, output)

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
    type=bool,
    default=False,
    help="Remove original file after conversion",
)
@click.argument(
    "source",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=Path("~/Pictures/wallpapers").expanduser(),
)
def wpconvert(extension: str, delete: bool, source: Path) -> None:
    """Convert images by extension `extension` to PNG."""
    source = Path(source)

    if extension in ["gif"]:
        click.secho("Cannot convert gif to png!", fg="red")

    from .tools.converter import convert_wallpapers

    convert_wallpapers(extension, delete, source)
