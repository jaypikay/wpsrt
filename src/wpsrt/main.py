from pathlib import Path

import click

from .wallpapers import move_wallpaper, scan_directory


@click.command()
@click.argument(
    "source",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=Path("~/Pictures/wallpapers").expanduser(),
)
@click.argument(
    "target",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
    default=Path("~/Pictures/wallpapers/by-resolution").expanduser(),
)
def wpsort(source: Path, target: Path) -> None:
    """Sort wallpapers found in source path to target location"""
    source = Path(source)
    target = Path(target)
    if not target.exists():
        target.mkdir()

    click.echo(f"Scanning wallpaper directory {source}...")
    wallpapers = [wallpaper for wallpaper in scan_directory(source)]
    with click.progressbar(wallpapers, label="Sorting wallpapers") as progress:
        for filename, (xres, yres) in progress:
            if filename.is_relative_to(target):
                continue
            new_filename = move_wallpaper(
                filename, target / f"{xres}x{yres}/{filename.name}"
            )
            click.echo(new_filename)
