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
        "tighs",
        "underboob",
        "underwear",
        "vagina",
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
