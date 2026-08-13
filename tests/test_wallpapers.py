from __future__ import annotations

from pathlib import Path

from PIL import Image

from wpsrt.errors import SkipUnsupportedImage
from wpsrt.wallpapers import move_wallpaper, scan_directory, sort_wallpapers


def test_scan_directory(temp_dir: Path):
    f1 = temp_dir / "a.png"
    f2 = temp_dir / "sub" / "b.jpg"
    f2.parent.mkdir()
    f1.write_text("a")
    f2.write_text("b")

    found = set(scan_directory(temp_dir))
    assert f1 in found
    assert f2 in found


def test_move_wallpaper(temp_dir: Path):
    src = temp_dir / "source.png"
    src.write_text("test")
    target = temp_dir / "dest_folder" / "source.png"

    moved = move_wallpaper(src, target)
    assert moved == target
    assert not src.exists()
    assert target.exists()


def test_sort_wallpapers_resolution(temp_dir: Path):
    source = temp_dir / "src"
    target = temp_dir / "dst"
    source.mkdir()

    img_path = source / "wp1.png"
    img = Image.new("RGB", (800, 600), color="red")
    img.save(img_path)

    sort_wallpapers("resolution", source, target, dry_run=False)

    expected = target / "by-resolution" / "800x600" / "wp1.png"
    assert expected.exists()


def test_skip_unsupported_image_counter():
    SkipUnsupportedImage.reset_count()
    assert SkipUnsupportedImage.count() == 0
    _ = SkipUnsupportedImage()
    assert SkipUnsupportedImage.count() == 1
    SkipUnsupportedImage.reset_count()
    assert SkipUnsupportedImage.count() == 0
