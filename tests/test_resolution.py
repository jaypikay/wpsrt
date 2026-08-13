from __future__ import annotations

from pathlib import Path

import pytest

from wpsrt.errors import SkipUnsupportedImage
from wpsrt.methods.resolution import process_file


def test_process_file_resolution(sample_image: Path):
    res = process_file(sample_image)
    assert res == Path(f"by-resolution/1920x1080/{sample_image.name}")


def test_process_file_invalid_image(temp_dir: Path):
    invalid_file = temp_dir / "invalid.jpg"
    invalid_file.write_text("corrupted image data")

    with pytest.raises(SkipUnsupportedImage):
        process_file(invalid_file)
