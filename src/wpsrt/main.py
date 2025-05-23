from pathlib import Path

import click

from .wallpapers import sort_wallpapers, hash_wallpapers


@click.command()
@click.option(
    "-m",
    "--mode",
    type=click.Choice(["resolution", "ratio", "hash"]),
    default="resolution",
    help="Sort by resolution or apsect ration",
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
    """Sort wallpapers found in source path to target location"""
    source = Path(source)
    target = Path(target)
    if not target.exists():
        target.mkdir(parents=True)

    if mode in ["resolution", "ratio"]:
        sort_wallpapers(mode, source, target)
    elif mode in ["hash"]:
        hash_wallpapers(target)
