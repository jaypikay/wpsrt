from pathlib import Path

from nudenet import NudeDetector

Detector = NudeDetector()

FOLDER_PREFIX = "rating"


NSFW_THRESHOLDS = {
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
    # "FEET_COVERED": 0.9,  # classifier is ignored
    "FEET_EXPOSED": 0.2,
    "FEMALE_BREAST_COVERED": 0.25,
    "FEMALE_BREAST_EXPOSED": 0.20,
    "FEMALE_GENITALIA_COVERED": 0.7,
    "FEMALE_GENITALIA_EXPOSED": 0.4,
    "MALE_BREAST_EXPOSED": 0.5,
    "MALE_GENITALIA_EXPOSED": 0.4,
}


def reinitialize_detector(onnx_model_path: Path) -> NudeDetector:
    global Detector
    Detector = NudeDetector(model_path=onnx_model_path)
    return Detector


def has_identifier_above_theshold(
    dataset: list, class_name: str, threshold: float = 0.7
) -> bool:
    return any(
        item["class"] == class_name and item["score"] > threshold for item in dataset
    )


def exeeds_nsfw_threshold(data) -> list:
    return [
        item["class"]
        for item in data
        if item["class"] in NSFW_THRESHOLDS
        and item["score"] > NSFW_THRESHOLDS[item["class"]]
    ]


def process_file(filename: Path) -> Path:
    detection = Detector.detect(filename.as_posix())
    if detection:
        exceeds = exeeds_nsfw_threshold(detection)
        if exceeds:
            return Path(f"{FOLDER_PREFIX}/NSFW/{filename.name}")
    return Path(f"{FOLDER_PREFIX}/SFW/{filename.name}")
