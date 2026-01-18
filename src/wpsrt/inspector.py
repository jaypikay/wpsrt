from pathlib import Path

import click
from nudenet import NudeDetector

from wpsrt.wallpapers import scan_directory


def grep_beautifier(classification: dict) -> str:
    output = []
    for data in classification:
        output.append(f"{data['class']}={data['score']}")
    if output:
        return ":".join(output)
    else:
        return "SFW"


def analyse_image(detector: NudeDetector, image: str):
    classification = detector.detect(image)
    click.echo(f"{image}:nudenet:{grep_beautifier(classification)}")


@click.command()
@click.option(
    "-n",
    "--nsfw-model",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default=None,
)
@click.argument(
    "target",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=Path("~/Pictures/wallpapers").expanduser(),
)
def nsfw_inspect(nsfw_model: Path, target: Path) -> None:
    if nsfw_model and Path(nsfw_model).exists():
        detector = NudeDetector(model_path=nsfw_model)
    else:
        detector = NudeDetector()

    target = Path(target)
    if target.is_dir():
        found_files = [f.as_posix() for f in scan_directory(target)]
        if len(found_files) > 100:
            msg = " this may take a while, please wait"
        else:
            msg = ""
        click.echo(f"Processing {len(found_files)}{msg}...", err=True)
        for fname in found_files:
            analyse_image(detector, fname)
    else:
        analyse_image(detector, target.as_posix())
