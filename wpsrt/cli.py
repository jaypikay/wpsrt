from pathlib import Path

import click

from .wallpapers import scan_directory


@click.command()
@click.argument(
    "directory", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
def sort(directory):
    for image in scan_directory(Path(directory).expanduser()):
        click.echo(image)


if __name__ == "__main__":
    sort(None)
