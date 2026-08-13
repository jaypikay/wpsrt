from __future__ import annotations

from pathlib import Path

from PIL import Image

from wpsrt.tools.converter import convert_wallpapers


def test_convert_wallpapers(temp_dir: Path):
    source = temp_dir / "src"
    source.mkdir()

    webp_file = source / "test.webp"
    img = Image.new("RGB", (100, 100), color="green")
    img.save(webp_file, format="WEBP")

    convert_wallpapers("webp", remove_original=True, source=source)

    png_file = source / "test.png"
    assert png_file.exists()
    assert not webp_file.exists()
