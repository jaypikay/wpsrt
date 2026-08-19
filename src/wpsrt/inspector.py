from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import click

from wpsrt.tools.log import setup_logging
from wpsrt.wallpapers import scan_directory

logger = logging.getLogger(__name__)


def grep_beautifier(classification: list[dict[str, Any]]) -> str:
    """Formats classification detection results into key=value output string."""
    output = [f"{data['class']}={data['score']}" for data in classification]
    return ":".join(output) if output else "SFW"


def analyse_image(detector: Any, image: str) -> None:
    """Detects content of an image file and prints formatted output."""
    classification = detector.detect(image)
    logger.debug("Detected %s for %s", grep_beautifier(classification), image)
    click.echo(f"{image}:nudenet:{grep_beautifier(classification)}")


analyze_image = analyse_image


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
def nsfw_inspect(nsfw_model: Path | None, target: Path) -> None:
    """Inspects wallpapers using NudeDetector and prints classifications."""
    setup_logging()
    from wpsrt.methods.nsfw import create_detector

    detector = create_detector(
        nsfw_model if nsfw_model and Path(nsfw_model).exists() else None
    )

    target = Path(target)
    if target.is_dir():
        found_files = [f.as_posix() for f in scan_directory(target)]
        msg = " this may take a while, please wait" if len(found_files) > 100 else ""
        logger.info("Processing %d file(s) from %s", len(found_files), target)
        click.echo(f"Processing {len(found_files)}{msg}...", err=True)
        for fname in found_files:
            analyse_image(detector, fname)
    else:
        analyse_image(detector, target.as_posix())
