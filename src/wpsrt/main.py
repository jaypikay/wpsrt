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

from wpsrt.config import Config
from wpsrt.tools.log import setup_logging

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "-m",
    "--mode",
    type=click.Choice(["resolution", "ratio", "nsfw", "clip"]),
    default=Config.sorting_algorithm,
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
    default=Path(Config.source_directory).expanduser(),
)
@click.argument(
    "target",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
    default=Path(Config.target_directory).expanduser(),
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
    _ = setup_logging()
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
    type=click.Choice(["clean", "hash", "compare", "tag"]),
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
@click.option(
    "--refresh",
    is_flag=True,
    default=False,
    help="Re-tag all images, replacing previously stored tags (tag mode only).",
)
@click.option(
    "--clean",
    is_flag=True,
    default=False,
    help="Remove hash entries for images no longer on the filesystem (tag mode only).",
)
@click.argument(
    "target",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=Path("~/Pictures/Wallpapers/").expanduser(),
)
def wphash(
    target: Path,
    mode: str,
    hash_method: str,
    threshold: int,
    output: Path | None,
    refresh: bool,
    clean: bool,
) -> None:
    """Hash, compare and clean image hashes.

    Example usage:

        wphash -m compare | swiv -t -i

        wphash -m compare -o similarities.dhash

        wphash -m tag --refresh

        wphash -m tag --clean
    """
    _ = setup_logging()
    target = Path(target)
    logger.info(
        "wphash invoked: mode=%s hash_method=%s threshold=%s target=%s refresh=%s clean=%s",
        mode,
        hash_method,
        threshold,
        target,
        refresh,
        clean,
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

    if mode == "tag":
        from .tools.hashing import tag_wallpapers

        tag_wallpapers(refresh=refresh, clean=clean)


def _render_tags_table(rows: list[tuple[str, int]]) -> None:
    """Print the list of used tags as an aligned table."""
    tag_width = max(len("TagName"), *(len(name) for name, _ in rows))
    count_width = max(len("Count"), *(len(str(count)) for _, count in rows))
    click.echo(f"| {'TagName':<{tag_width}} | {'Count':>{count_width}} |")
    click.echo(f"|{'-' * (tag_width + 2)}|{'-' * (count_width + 2)}|")
    for name, count in rows:
        click.echo(f"| {name:<{tag_width}} | {count:>{count_width}} |")


@click.command()
@click.option(
    "-l",
    "--limit",
    type=int,
    default=None,
    help="Maximum number of results to display.",
)
@click.option(
    "-t",
    "--list-tags",
    is_flag=True,
    default=False,
    help="List all used tags with counts instead of searching.",
)
@click.argument("filters", nargs=-1)
def wpsearch(filters: tuple[str, ...], limit: int | None, list_tags: bool) -> None:
    """Search hashed wallpapers by vision-model tags.

    Filters use a 'tag:' prefix. A quoted value is treated as a single tag
    name when it matches exactly, otherwise it is split into individual tags
    that must all be present on the image:

        wpsearch tag:cyberpunk

        wpsearch tag:'cyberpunk city'

        is equivalent to:

        wpsearch tag:cyberpunk tag:city

      Use --list-tags to show all tags stored in the database.
    """
    _ = setup_logging()
    from .tools import hashing

    if list_tags:
        rows = hashing.list_tags()
        if not rows:
            click.echo("No tags found.")
            return
        _render_tags_table(rows)
        return

    known_tags = hashing.get_all_tags()
    tag_names: list[str] = []
    missing: list[str] = []
    for raw in filters:
        if not raw.startswith("tag:"):
            raise click.BadParameter(
                f"Unknown filter '{raw}', expected 'tag:NAME'", param_hint="FILTER"
            )
        value = raw[4:].strip().lower()
        expanded = [value] if value in known_tags else value.split()
        for name in expanded:
            if name not in known_tags and name not in missing:
                missing.append(name)
        tag_names.extend(expanded)

    if missing:
        logger.warning("Tag(s) not found in database: %s", ", ".join(missing))

    if not tag_names:
        logger.warning("No tags given to search for.")
        return

    results = hashing.search_image_tags(tag_names)
    if limit is not None:
        results = results[:limit]

    logger.info("wpsearch: filters=%s found=%d", filters, len(results))
    click.echo(f"Found {len(results)} matching image(s):")
    for filename, assigned in results:
        click.echo(f"  {filename}")
        for tag, confidence in assigned:
            click.echo(f"      {tag} ({confidence:.2f})")


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
    _ = setup_logging()
    source = Path(source)
    logger.info(
        "wpsrt-convert invoked: extension=%s delete=%s source=%s",
        extension,
        delete,
        source,
    )

    if extension.lower().strip(".") == "gif":
        logger.warning("Refused to convert gif to png for source=%s", source)
        return

    from .tools.converter import convert_wallpapers

    convert_wallpapers(extension, delete, source)
