from __future__ import annotations

from pathlib import Path

import pytest

from wpsrt.errors import SkipUnsupportedImage
from wpsrt.methods.aspectratio import calculate_aspect_ratio, process_file


def test_calculate_aspect_ratio():
    assert calculate_aspect_ratio(1920, 1080) == "16:9"
    assert calculate_aspect_ratio(2560, 1440) == "16:9"
    assert calculate_aspect_ratio(1024, 768) == "4:3"
    assert calculate_aspect_ratio(1080, 1080) == "1:1"


def test_process_file_aspect_ratio(sample_image: Path):
    res = process_file(sample_image)
    assert res == Path(f"by-ratio/16:9/{sample_image.name}")


def test_process_file_invalid_image(temp_dir: Path):
    invalid_file = temp_dir / "invalid.png"
    invalid_file.write_text("not an image")

    with pytest.raises(SkipUnsupportedImage):
        process_file(invalid_file)
