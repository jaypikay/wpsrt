from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import nudenet
import onnxruntime
from nudenet import NudeDetector

from wpsrt.tools.device import onnx_providers

logger = logging.getLogger(__name__)

FOLDER_PREFIX = "rating"

NSFW_THRESHOLDS: dict[str, float] = {
    "ANUS_COVERED": 0.5,
    "ANUS_EXPOSED": 0.4,
    "ARMPITS_COVERED": 0.9,
    "ARMPITS_EXPOSED": 0.25,
    "BELLY_COVERED": 0.5,
    "BELLY_EXPOSED": 0.25,
    "BUTTOCKS_COVERED": 0.35,
    "BUTTOCKS_EXPOSED": 0.2,
    "FACE_FEMALE": 0.95,
    "FACE_MALE": 0.95,
    "FEET_EXPOSED": 0.2,
    "FEMALE_BREAST_COVERED": 0.25,
    "FEMALE_BREAST_EXPOSED": 0.20,
    "FEMALE_GENITALIA_COVERED": 0.7,
    "FEMALE_GENITALIA_EXPOSED": 0.4,
    "MALE_BREAST_EXPOSED": 0.5,
    "MALE_GENITALIA_EXPOSED": 0.4,
}

_detector: NudeDetector | None = None


class ProviderAwareNudeDetector(NudeDetector):
    """NudeDetector variant that picks onnxruntime execution providers explicitly.

    The upstream ``NudeDetector`` accepts a ``providers`` argument but ignores
    it, silently letting onnxruntime pick the first available execution
    provider. This subclass hands the session an explicit provider list from
    :func:`wpsrt.tools.device.onnx_providers`, preferring the AMD ROCm GPU
    and falling back to the CPU provider.
    """

    def __init__(self, model_path: str | None = None, inference_resolution: int = 320):
        model_file = (
            os.path.join(os.path.dirname(nudenet.__file__), "320n.onnx")
            if model_path is None
            else model_path
        )
        self.onnx_session = onnxruntime.InferenceSession(
            model_file, providers=onnx_providers()
        )
        model_inputs = self.onnx_session.get_inputs()
        self.input_width = inference_resolution
        self.input_height = inference_resolution
        self.input_name = model_inputs[0].name


def create_detector(model_path: str | Path | None = None) -> ProviderAwareNudeDetector:
    """Creates a provider-aware NudeDetector for the given ONNX model."""
    logger.info(
        "Initializing NudeDetector%s",
        f" with model {model_path}" if model_path else " with default model",
    )
    return ProviderAwareNudeDetector(model_path=str(model_path) if model_path else None)


def get_detector() -> NudeDetector:
    """Returns the NudeDetector instance, instantiating it lazily if needed."""
    global _detector
    if _detector is None:
        _detector = create_detector()
    return _detector


def reinitialize_detector(onnx_model_path: Path | str) -> None:
    """Reinitializes the detector with a custom ONNX model path."""
    global _detector
    logger.info("Reinitializing NudeDetector with model %s", onnx_model_path)
    _detector = create_detector(onnx_model_path)


def has_identifier_above_threshold(
    dataset: list[dict[str, Any]], class_name: str, threshold: float = 0.7
) -> bool:
    """Checks if any item in dataset matches class_name and exceeds threshold."""
    return any(
        item["class"] == class_name and item["score"] > threshold for item in dataset
    )


# Alias for backwards compatibility
has_identifier_above_theshold = has_identifier_above_threshold


def exceeds_nsfw_threshold(data: list[dict[str, Any]]) -> list[str]:
    """Returns classes from detection data that exceed configured NSFW thresholds."""
    return [
        item["class"]
        for item in data
        if item["class"] in NSFW_THRESHOLDS
        and item["score"] > NSFW_THRESHOLDS[item["class"]]
    ]


# Alias for backwards compatibility
exeeds_nsfw_threshold = exceeds_nsfw_threshold


def process_file(filename: Path) -> Path:
    """Processes an image file with NudeDetector and returns rating path."""
    detector = get_detector()
    detection = detector.detect(filename.as_posix())
    if detection:
        exceeds = exceeds_nsfw_threshold(detection)
        if exceeds:
            logger.debug("NSFW classes exceeded for %s: %s", filename, exceeds)
            return Path(f"{FOLDER_PREFIX}/NSFW/{filename.name}")
    return Path(f"{FOLDER_PREFIX}/SFW/{filename.name}")
