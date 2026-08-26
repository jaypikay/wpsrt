from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import torch
from PIL import Image, UnidentifiedImageError

from wpsrt.config import Config
from wpsrt.errors import SkipCLipSortingThreshold, SkipUnsupportedImage
from wpsrt.tags import CLASSES, LABELS, LOOKUP_TABLE
from wpsrt.tools.device import get_torch_device

logger = logging.getLogger(__name__)

FOLDER_PREFIX = "rating"

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


def embed_with_prompt_ensemble(
    model: Any, labels: list[str], templates: tuple[str, ...]
) -> Any:
    """Embeds labels with a prompt ensemble, averaging per label to remove
    template-specific bias.

    Args:
        model: The loaded CLIP sentence-transformers model.
        labels: The concepts to embed.
        templates: Prompt templates, each containing a ``{label}`` placeholder.

    Returns:
        A normalized tensor of shape ``(len(labels), embedding_dim)``.
    """
    prompts = [
        template.format(label=label) for label in labels for template in templates
    ]
    embeddings = model.encode(
        prompts,
        convert_to_tensor=True,
        normalize_embeddings=True,
        device=str(get_torch_device()),
    )
    averaged = embeddings.reshape(len(labels), len(templates), -1).mean(dim=1)
    return torch.nn.functional.normalize(averaged, dim=-1)


def _encode_label_embeddings(model: Any) -> Any:
    """Embeds every rating label with the prompt ensemble and averages per label."""
    return embed_with_prompt_ensemble(model, LABELS, PROMPT_TEMPLATES)


def load_model() -> Any:
    """Returns the shared CLIP sentence-transformers model, loading it once.

    The model is cached module-wide so that sorting and tagging modes never
    initialise the transformer twice, saving time and memory.

    Returns:
        The loaded ``SentenceTransformer`` instance.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        device = get_torch_device()
        logger.info("Loading CLIP model clip-ViT-B-32 on %s", device)
        _model = SentenceTransformer("clip-ViT-B-32").to(device)
    return _model


def _get_model_and_embeddings() -> tuple[Any, Any]:
    global _embeddings
    if _embeddings is None:
        _embeddings = _encode_label_embeddings(load_model())
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

    try:
        with Image.open(filename) as image:
            rgb_image = image.convert("RGB")
    except OSError:
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

    # TODO: raise SkipCLipSortingThreshold if confidence < threshold (configurable)
    if confidence < Config.clip_threshold:
        logger.warning(
            "Skipping file below CLIP threshold (%0.2f < %0.2f): %s",
            confidence,
            Config.clip_threshold,
            filename,
        )
        raise SkipCLipSortingThreshold from None

    target_path = Path(f"{FOLDER_PREFIX}/{classification}/{filename.name}")
    logger.info(
        f"File: {target_path}, CLIP Classification: {classification} ({label_name}, confidence {confidence:.2f})"
    )

    return target_path
