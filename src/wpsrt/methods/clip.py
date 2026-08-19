from __future__ import annotations

import logging
from itertools import chain
from pathlib import Path
from typing import Any

import click
import torch
from PIL import Image, UnidentifiedImageError

from wpsrt.tools.device import get_torch_device

logger = logging.getLogger(__name__)

FOLDER_PREFIX = "rating"

CLASS_LABELS: dict[str, list[str]] = {
    "SFW": [
        "abstract",
        "animal",
        "anime",
        "architecture",
        "art",
        "building",
        "car",
        "cityscape",
        "clothed person",
        "clothing",
        "comic",
        "cyberpunk",
        "cyborg",
        "everyday scene",
        "family",
        "fantasy",
        "food",
        "furniture",
        "group of people",
        "house",
        "interior design",
        "landscape",
        "manga",
        "movie",
        "nature",
        "object",
        "other",
        "outdoor scene",
        "painting",
        "person",
        "plant",
        "portrait",
        "post-apocalyptic",
        "robots",
        "scenery",
        "sculpture",
        "skeleton",
        "skulls",
        "space",
        "sports",
        "street",
        "super hero",
        "technology",
        "tree",
        "vehicle",
        "water",
    ],
    "NSFW": [
        "bare feet",
        "belly",
        "belly button",
        "bikini",
        "cleavage",
        "erotic",
        "kissing",
        "lingerie",
        "micro bikini",
        "sexy",
        "swimsuit",
        "thighs",
        "thong",
        "underboob",
        "underwear",
        "adult content",
        "anal sex",
        "anus",
        "ass",
        "bdsm",
        "bent over",
        "big breasts",
        "blowjob",
        "bondage",
        "boobs",
        "breasts",
        "butt",
        "cameltoe",
        "cum",
        "cunnilingus",
        "dick",
        "dildo",
        "ejaculation",
        "erection",
        "explicit",
        "fellatio",
        "fingering",
        "genitals",
        "hentai",
        "intercourse",
        "masturbation",
        "mons veneris",
        "mound of venus",
        "naked",
        "nipple",
        "nipples",
        "nude",
        "nudity",
        "onlyfans",
        "orgasm",
        "orgy",
        "penetration",
        "penis",
        "phallus",
        "porn",
        "pornography",
        "pubic hair",
        "pubic mound",
        "pussy",
        "rule 34",
        "semen",
        "sex",
        "sex toy",
        "sexual act",
        "sexual intercourse",
        "small breasts",
        "sperm",
        "spread legs",
        "striptease",
        "testicles",
        "tits",
        "vagina",
        "vibrator",
        "vulva",
        "xxx",
    ],
}
LABELS = list(chain.from_iterable(CLASS_LABELS.values()))
LOOKUP_TABLE = {v: k for k, lst in CLASS_LABELS.items() for v in lst}
CLASSES = list(CLASS_LABELS)

PROMPT_TEMPLATES: tuple[str, ...] = (
    "a photo of {label}",
    "an illustration of {label}",
    "a painting of {label}",
    "a digital artwork of {label}",
    "a wallpaper showing {label}",
)
"""Prompt ensemble used to embed each label, averaging out template-specific bias."""

LOGIT_SCALE = 100.0
"""CLIP's trained logit scale, used to turn cosine similarities into probabilities."""

LABEL_CLASS_INDEX = torch.tensor(
    [CLASSES.index(LOOKUP_TABLE[label]) for label in LABELS]
)

_model: Any = None
_embeddings: Any = None


def _encode_label_embeddings(model: Any) -> Any:
    """Embeds every label with the prompt ensemble and averages per label.

    Args:
        model: The loaded CLIP sentence-transformers model.

    Returns:
        A normalized tensor of shape ``(len(LABELS), embedding_dim)``.
    """
    prompts = [
        template.format(label=label)
        for label in LABELS
        for template in PROMPT_TEMPLATES
    ]
    embeddings = model.encode(
        prompts,
        convert_to_tensor=True,
        normalize_embeddings=True,
        device=str(get_torch_device()),
    )
    averaged = embeddings.reshape(len(LABELS), len(PROMPT_TEMPLATES), -1).mean(dim=1)
    return torch.nn.functional.normalize(averaged, dim=-1)


def _get_model_and_embeddings() -> tuple[Any, Any]:
    global _model, _embeddings
    if _model is None or _embeddings is None:
        from sentence_transformers import SentenceTransformer

        device = get_torch_device()
        logger.info("Loading CLIP model clip-ViT-B-32 on %s", device)
        _model = SentenceTransformer("clip-ViT-B-32").to(device)
        _embeddings = _encode_label_embeddings(_model)
    return _model, _embeddings


def classify_scores(cos_scores: Any) -> tuple[str, str, float]:
    """Aggregates per-label similarities into a class-level decision.
    Instead of trusting a single best-matching label, the label similarities are
    turned into probabilities and summed per class, so a lone outlier label
    cannot decide the classification on its own.

    Args:
        cos_scores: Cosine similarities against every entry of ``LABELS``.

    Returns:
        A tuple of the winning class name, the best-matching label and the
        confidence of the winning class in the range ``0.0`` to ``1.0``.
    """
    cos_scores = cos_scores.detach().cpu()
    probs = torch.softmax(cos_scores.flatten() * LOGIT_SCALE, dim=-1)
    class_probs = torch.zeros(len(CLASSES), dtype=probs.dtype)
    class_probs.index_add_(0, LABEL_CLASS_INDEX, probs)
    class_idx = int(torch.argmax(class_probs).item())
    label_name = LABELS[int(torch.argmax(probs).item())]
    return CLASSES[class_idx], label_name, float(class_probs[class_idx].item())


def score_file(filename: Path) -> float:
    """Processes an image file with CLIP and returns the confidence score."""
    from sentence_transformers import util

    model, embeddings = _get_model_and_embeddings()
    try:
        with Image.open(filename) as image:
            rgb_image = image.convert("RGB")
            img = model.encode(
                [rgb_image],
                convert_to_tensor=True,
                normalize_embeddings=True,
                device=str(get_torch_device()),
            )
            cos_scores = util.cos_sim(img, embeddings)
            _, _, confidence = classify_scores(cos_scores)
            return confidence
    except (UnidentifiedImageError, OSError):
        click.secho(
            f"Skipping unsupported image format: {filename}", fg="yellow", err=True
        )
        logger.warning("Skipping unsupported image format: %s", filename)
    return -1.0


def process_file(filename: Path) -> Path:
    """Processes an image file with the CLIP model and returns its target path.

    Args:
        filename: Path of the image to classify.

    Returns:
        The destination path below ``FOLDER_PREFIX`` for the detected class.

    Raises:
        SkipUnsupportedImage: If the file cannot be read as an image.
    """
    from wpsrt.errors import SkipUnsupportedImage

    try:
        with Image.open(filename) as image:
            rgb_image = image.convert("RGB")
    except OSError:
        click.secho(
            f"WARN: Skipping unsupported file: {filename}", fg="yellow", err=True
        )
        logger.warning("Skipping unsupported file: %s", filename)
        raise SkipUnsupportedImage from None

    from sentence_transformers import util

    model, embeddings = _get_model_and_embeddings()
    img = model.encode(
        [rgb_image],
        convert_to_tensor=True,
        normalize_embeddings=True,
        device=str(get_torch_device()),
    )
    cos_scores = util.cos_sim(img, embeddings)
    classification, label_name, confidence = classify_scores(cos_scores)

    target_path = Path(f"{FOLDER_PREFIX}/{classification}/{filename.name}")
    logger.info(
        f"File: {target_path}, CLIP Classification: {classification} ({label_name}, confidence {confidence:.2f})"
    )

    return target_path
