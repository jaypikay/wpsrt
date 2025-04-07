from pathlib import Path

import click

from .wallpapers import calculate_aspect_ratio, move_wallpaper, scan_directory


@click.command()
@click.option(
    "-m",
    "--mode",
    type=click.Choice(["resolution", "ratio"]),
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
        target.mkdir()

    click.echo(f"Scanning wallpaper directory {source}...")
    wallpapers = [wallpaper for wallpaper in scan_directory(source)]
    moved_files = []
    with click.progressbar(wallpapers, label="Sorting wallpapers") as progress:
        for filename, (xres, yres) in progress:
            if mode == "resolution":
                if filename.is_relative_to(target / f"by-resolution/{xres}x{yres}"):
                    continue
                new_filename = move_wallpaper(
                    filename, target / f"by-resolution/{xres}x{yres}/{filename.name}"
                )
            else:
                ratio = calculate_aspect_ratio(xres, yres)
                if filename.is_relative_to(target / f"by-aspect-ratio/{ratio}"):
                    continue
                new_filename = move_wallpaper(
                    filename, target / f"by-aspect-ratio/{ratio}/{filename.name}"
                )
            moved_files.append(new_filename)

    click.echo(f"Moved {len(moved_files)} files.")
    for filename in moved_files:
        click.echo(f"- {filename}")
