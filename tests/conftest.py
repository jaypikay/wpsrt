from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_image(temp_dir: Path) -> Path:
    img_path = temp_dir / "test_1920x1080.png"
    img = Image.new("RGB", (1920, 1080), color="blue")
    img.save(img_path)
    return img_path
