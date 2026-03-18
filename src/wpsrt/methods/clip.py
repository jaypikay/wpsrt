from itertools import chain
from pathlib import Path

import click
import torch
from PIL import Image, UnidentifiedImageError
from sentence_transformers import SentenceTransformer, util

from wpsrt.errors import SkipUnsupportedImage

FOLDER_PREFIX = "rating"

en_model = SentenceTransformer("clip-ViT-B-32")

CLASS_LABELS = {
    "SFW": [
        "landscape",
        "other",
        "cyberpunk",
        "post-apocalyptic",
        "space",
        "fantasy",
        "anime",
        "manga",
        "comic",
        "movie",
        "super hero",
        "object",
        "abstract",
    ],
    "NSFW": [
        "mons veneris",
        "pubic mound",
        "mound of venus",
        "naked",
        "nude",
        "porn",
        "erotic",
        "butt",
        "ass",
        "anus",
        "vagina",
        "bent over",
        "belly button",
        "belly",
        "boobs",
        "big breasts",
        "underboob",
        "breasts",
        "nipple",
        "nipples",
        "spread legs",
        "tighs",
        "sexy",
        "sex",
        "kissing",
        "lingerie",
        "underwear",
    ],
}
LABELS = list(chain.from_iterable(CLASS_LABELS.values()))
LOOKUP_TABLE = {v: k for k, lst in CLASS_LABELS.items() for v in lst}

en_emb = en_model.encode(LABELS, convert_to_tensor=True)


def process_file(filename: Path) -> Path:
    global en_model
    try:
        image = Image.open(filename)

        img = en_model.encode([image], convert_to_tensor=True)
        cos_scores = util.cos_sim(img, en_emb)
        label = torch.argmax(cos_scores, dim=1)
        label_name = LABELS[label]
        classification = LOOKUP_TABLE[label_name]

        return Path(f"{FOLDER_PREFIX}/{classification}/{filename.name}")
    except UnidentifiedImageError:
        click.secho(
            f"WARN: Skipping unsupported file: {filename}", fg="yellow", err=True
        )
        raise SkipUnsupportedImage
