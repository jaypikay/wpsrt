from __future__ import annotations

from itertools import chain
from pathlib import Path
from typing import Any

import click
import torch
from PIL import Image, UnidentifiedImageError

FOLDER_PREFIX = "rating"

CLASS_LABELS: dict[str, list[str]] = {
    "SFW": [
        "abstract",
        "anime",
        "comic",
        "cyberpunk",
        "cyborg",
        "fantasy",
        "landscape",
        "manga",
        "movie",
        "object",
        "other",
        "post-apocalyptic",
        "robots",
        "skeleton",
        "skulls",
        "space",
        "super hero",
    ],
    "NSFW": [
        "anus",
        "ass",
        "bare feet",
        "bdsm",
        "belly button",
        "belly",
        "bent over",
        "big breasts",
        "bondage",
        "boobs",
        "breasts",
        "butt",
        "erotic",
        "kissing",
        "lingerie",
        "mons veneris",
        "mound of venus",
        "naked",
        "nipple",
        "nipples",
        "nude",
        "penis",
        "porn",
        "pubic mound",
        "pussy",
        "sex",
        "sexy",
        "small breasts",
        "spread legs",
        "thighs",
        "underboob",
        "underwear",
        "vagina",
    ],
}
LABELS = list(chain.from_iterable(CLASS_LABELS.values()))
LOOKUP_TABLE = {v: k for k, lst in CLASS_LABELS.items() for v in lst}

_model: Any = None
_embeddings: Any = None


def _get_model_and_embeddings() -> tuple[Any, Any]:
    global _model, _embeddings
    if _model is None or _embeddings is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("clip-ViT-B-32")
        _embeddings = _model.encode(LABELS, convert_to_tensor=True)
    return _model, _embeddings


def process_file(filename: Path) -> Path:
    """Processes an image file with CLIP model and returns classification path."""
    from sentence_transformers import util

    from wpsrt.errors import SkipUnsupportedImage

    model, embeddings = _get_model_and_embeddings()
    try:
        with Image.open(filename) as image:
            img = model.encode([image], convert_to_tensor=True)
        cos_scores = util.cos_sim(img, embeddings)
        label_idx = int(torch.argmax(cos_scores, dim=1).item())
        label_name = LABELS[label_idx]
        classification = LOOKUP_TABLE[label_name]

        return Path(f"{FOLDER_PREFIX}/{classification}/{filename.name}")
    except UnidentifiedImageError:
        click.secho(
            f"WARN: Skipping unsupported file: {filename}", fg="yellow", err=True
        )
        raise SkipUnsupportedImage from None
