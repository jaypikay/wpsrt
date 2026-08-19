from __future__ import annotations

import logging
import os
from pathlib import Path

import click
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)


def score_file(filename: Path) -> float:
    """Processes an image file with OpenNSFW2 and returns the score.

    OpenNSFW2 and its TensorFlow backend are imported lazily so that running
    other wpsrt modes never requires a TensorFlow installation. TensorFlow
    transparently uses the AMD ROCm GPU when available and falls back to CPU.
    """
    os.environ.setdefault("TF_FORCE_GPU_ALLOW_GROWTH", "true")
    try:
        import opennsfw2 as n2
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "opennsfw2 requires a TensorFlow build; install the `rocm` extra "
            "(uv sync --extra rocm) or install TensorFlow for CPU."
        ) from exc

    try:
        with Image.open(filename) as img:
            score = n2.predict_image(img)
            return score
    except UnidentifiedImageError:
        click.secho(
            f"Skipping unsupported image format: {filename}", fg="yellow", err=True
        )
        logger.warning("Skipping unsupported image format: %s", filename)
    return -1


def process_file(_: Path) -> Path:
    """Processes an image file with OpenNSFW2 and returns rating path."""
    raise NotImplementedError("process_file is not implemented yet.")
