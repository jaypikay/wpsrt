"""Vision-model based tagging of hashed wallpapers.

Reuses the CLIP ``clip-ViT-B-32`` model already used by :mod:`wpsrt.methods.clip`
and a dedicated set of candidate tags to assign ranked tags to images.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import torch
from PIL import Image, UnidentifiedImageError

from wpsrt.methods import clip
from wpsrt.tags import UNIQUE_TAG_SET
from wpsrt.tools.device import get_torch_device

logger = logging.getLogger(__name__)

TAG_LABELS: list[str] = list(UNIQUE_TAG_SET)
"""Candidate tags assigned to hashed images by the CLIP vision model."""

PROMPT_TEMPLATES: tuple[str, ...] = (
    "a photo of {label}",
    "an illustration of {label}",
    "a painting of {label}",
    "a digital artwork of {label}",
    "a wallpaper showing {label}",
)
"""Prompt ensemble used to embed each tag, averaging out template-specific bias."""

DEFAULT_TOP_K = 5

_embeddings: Any = None


def _get_tag_embeddings() -> Any:
    """Embeds all tags once and caches the result module-wide."""
    global _embeddings
    if _embeddings is None:
        _embeddings = clip.embed_with_prompt_ensemble(
            clip.load_model(), TAG_LABELS, PROMPT_TEMPLATES
        )
    return _embeddings


def tag_file(
    filename: Path,
    top_k: int = DEFAULT_TOP_K,
    threshold: float | None = None,
) -> list[tuple[str, float]]:
    """Classifies an image with the CLIP vision model into ranked tags.

    The image is embedded with CLIP and compared against every candidate tag
    embedding; cosine similarities are turned into probabilities via the shared
    CLIP logit scale.

    Args:
        filename: Path of the image to tag.
        top_k: Maximum number of tags to return, descending by confidence.
        threshold: Tags with a confidence below this value are dropped from the
            result. If None, no filtering happens.

    Returns:
        A list of ``(tag, confidence)`` tuples, descending by confidence and
        filtered to tags whose confidence is at least ``threshold``.
    """
    from wpsrt.errors import SkipUnsupportedImage

    try:
        with Image.open(filename) as image:
            rgb_image = image.convert("RGB")
    except (UnidentifiedImageError, OSError):
        logger.warning("Skipping unsupported file: %s", filename)
        raise SkipUnsupportedImage from None

    from sentence_transformers import util

    model = clip.load_model()
    embeddings = _get_tag_embeddings()
    img = model.encode(
        [rgb_image],
        convert_to_tensor=True,
        normalize_embeddings=True,
        device=str(get_torch_device()),
    )
    cos_scores = util.cos_sim(img, embeddings)[0]
    probs = torch.softmax(cos_scores * clip.LOGIT_SCALE, dim=-1)
    top_indices = probs.argsort(descending=True)[:top_k]
    tags = [(TAG_LABELS[int(index)], float(probs[index])) for index in top_indices]
    if threshold is not None:
        tags = [
            (tag, confidence) for tag, confidence in tags if confidence >= threshold
        ]
    return tags
