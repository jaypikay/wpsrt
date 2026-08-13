from __future__ import annotations

from pathlib import Path
from typing import Any

from nudenet import NudeDetector

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


def get_detector() -> NudeDetector:
    """Returns the NudeDetector instance, instantiating it lazily if needed."""
    global _detector
    if _detector is None:
        _detector = NudeDetector()
    return _detector


def reinitialize_detector(onnx_model_path: Path | str) -> None:
    """Reinitializes the detector with a custom ONNX model path."""
    global _detector
    _detector = NudeDetector(model_path=str(onnx_model_path))


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
            return Path(f"{FOLDER_PREFIX}/NSFW/{filename.name}")
    return Path(f"{FOLDER_PREFIX}/SFW/{filename.name}")
