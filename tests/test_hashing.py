from __future__ import annotations

import logging
from pathlib import Path

import pytest
from click.testing import CliRunner

from wpsrt.main import wpsearch
from wpsrt.methods import tagging
from wpsrt.tools import hashing


@pytest.fixture
def hash_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(hashing, "DATA_DIR", tmp_path)
    monkeypatch.setattr(hashing, "DB_FILE", tmp_path / "wpsrt.sqlite")
    monkeypatch.setattr(hashing, "database_connection", None)
    return hashing.init_hashdb()


def _insert_hash(hash_db, uuid: str, filename: str) -> None:
    hash_db.execute(
        """INSERT INTO hashes (uuid, filename, phash, dhash, colorhash, average_hash, xres, yres)
           VALUES (?, ?, '', '', '', '', 1920, 1080)""",
        (uuid, filename),
    )
    hash_db.commit()


def test_init_hashdb_creates_tag_tables(hash_db):
    tables = {
        row[0]
        for row in hash_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"hashes", "tags", "image_tags"} <= tables


def test_store_image_tags_links_image_to_tags(hash_db):
    _insert_hash(hash_db, "u1", "/tmp/img1.jpg")

    hashing.store_image_tags(Path("/tmp/img1.jpg"), [("nature", 0.9), ("sky", 0.7)])

    rows = hash_db.execute(
        """SELECT t.name, it.confidence
           FROM image_tags it JOIN tags t ON t.id = it.tag_id"""
    ).fetchall()
    assert set(rows) == {("nature", 0.9), ("sky", 0.7)}


def test_store_image_tags_reuses_tag_rows(hash_db):
    _insert_hash(hash_db, "u1", "/tmp/img1.jpg")
    _insert_hash(hash_db, "u2", "/tmp/img2.jpg")

    hashing.store_image_tags(Path("/tmp/img1.jpg"), [("nature", 0.9)])
    hashing.store_image_tags(Path("/tmp/img2.jpg"), [("nature", 0.8)])

    tag_count = hash_db.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    assert tag_count == 1


def test_clear_image_tags_removes_links_not_tags(hash_db):
    _insert_hash(hash_db, "u1", "/tmp/img1.jpg")
    hashing.store_image_tags(Path("/tmp/img1.jpg"), [("nature", 0.9), ("sky", 0.6)])

    hashing.clear_image_tags(Path("/tmp/img1.jpg"))

    links = hash_db.execute("SELECT COUNT(*) FROM image_tags").fetchone()[0]
    tags = hash_db.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    assert links == 0
    assert tags == 2


def test_clear_image_tags_ignores_unhashed_file(hash_db):
    hashing.clear_image_tags(Path("/tmp/not-hashed.jpg"))
    assert hash_db.execute("SELECT COUNT(*) FROM image_tags").fetchone()[0] == 0


def test_store_image_tags_ignores_unhashed_file(hash_db):
    hashing.store_image_tags(Path("/tmp/not-hashed.jpg"), [("nature", 0.9)])
    assert hash_db.execute("SELECT COUNT(*) FROM image_tags").fetchone()[0] == 0


def test_get_tagged_filenames(hash_db):
    _insert_hash(hash_db, "u1", "/tmp/img1.jpg")
    _insert_hash(hash_db, "u2", "/tmp/img2.jpg")
    hashing.store_image_tags(Path("/tmp/img1.jpg"), [("nature", 0.9)])

    assert hashing.get_tagged_filenames() == {"/tmp/img1.jpg"}


def test_fetch_untagged_filenames(hash_db):
    _insert_hash(hash_db, "u1", "/tmp/img1.jpg")
    _insert_hash(hash_db, "u2", "/tmp/img2.jpg")
    hashing.store_image_tags(Path("/tmp/img1.jpg"), [("nature", 0.9)])

    assert hashing.fetch_untagged_filenames() == [Path("/tmp/img2.jpg")]


def test_tag_wallpapers_tags_only_untagged(
    hash_db, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    img1 = temp_dir / "img1.png"
    img2 = temp_dir / "img2.png"
    img1.write_text("image data")
    img2.write_text("image data")
    _insert_hash(hash_db, "u1", img1.as_posix())
    _insert_hash(hash_db, "u2", img2.as_posix())
    hashing.store_image_tags(img1, [("nature", 0.9)])

    monkeypatch.setattr(
        tagging, "tag_file", lambda filename, top_k=5, threshold=None: [("sky", 0.8)]
    )

    hashing.tag_wallpapers()

    assert hashing.get_tagged_filenames() == {img1.as_posix(), img2.as_posix()}


def test_tag_wallpapers_refresh_replaces_existing_tags(
    hash_db, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    img = temp_dir / "img.png"
    img.write_text("image data")
    _insert_hash(hash_db, "u1", img.as_posix())
    hashing.store_image_tags(img, [("nature", 0.9)])

    monkeypatch.setattr(
        tagging, "tag_file", lambda filename, top_k=5, threshold=None: [("city", 0.8)]
    )

    hashing.tag_wallpapers(refresh=True)

    assert hashing.search_image_tags(["nature"]) == []
    matches = hashing.search_image_tags(["city"])
    assert matches and matches[0][0] == img.as_posix()
    assert dict(matches[0][1]) == {"city": 0.8}


def test_tag_wallpapers_without_refresh_keeps_existing_tags(
    hash_db, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    img = temp_dir / "img.png"
    img.write_text("image data")
    _insert_hash(hash_db, "u1", img.as_posix())
    hashing.store_image_tags(img, [("nature", 0.9)])

    monkeypatch.setattr(
        tagging, "tag_file", lambda filename, top_k=5, threshold=None: [("city", 0.8)]
    )

    hashing.tag_wallpapers()

    matches = hashing.search_image_tags(["nature"])
    assert matches and matches[0][0] == img.as_posix()


def test_tag_wallpapers_skips_image_below_threshold(
    hash_db, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    img = temp_dir / "img.png"
    img.write_text("image data")
    _insert_hash(hash_db, "u1", img.as_posix())

    monkeypatch.setattr(
        tagging, "tag_file", lambda filename, top_k=5, threshold=None: []
    )

    hashing.tag_wallpapers()

    assert hashing.get_tagged_filenames() == set()


def test_tag_wallpapers_uses_config_threshold(
    hash_db, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    img = temp_dir / "img.png"
    img.write_text("image data")
    _insert_hash(hash_db, "u1", img.as_posix())

    received_thresholds: list[float] = []

    def fake_tag_file(filename, top_k=5, threshold=None):
        received_thresholds.append(threshold)
        return [("city", 0.8)]

    monkeypatch.setattr(tagging, "tag_file", fake_tag_file)

    hashing.tag_wallpapers()

    assert received_thresholds == [hashing.Config.clip_threshold]
    assert hashing.get_tagged_filenames() == {img.as_posix()}


def test_cleanup_hashes_removes_stale_entries(hash_db, temp_dir: Path):
    missing_file = temp_dir / "missing.png"
    missing_file.write_text("image data")
    _insert_hash(hash_db, "u1", missing_file.as_posix())
    hashing.store_image_tags(missing_file, [("nature", 0.9)])
    missing_file.unlink()

    present_file = temp_dir / "present.png"
    present_file.write_text("image data")
    _insert_hash(hash_db, "u2", present_file.as_posix())

    hashing.cleanup_hashes()

    assert missing_file not in [Path(f) for f in hashing.get_hashed_filenames()]
    assert present_file.as_posix() in hashing.get_hashed_filenames()
    assert hashing.get_tagged_filenames() == set()


def test_tag_wallpapers_clean_drops_inaccessible_images(
    hash_db, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    missing_file = temp_dir / "missing.png"
    missing_file.write_text("image data")
    _insert_hash(hash_db, "u1", missing_file.as_posix())
    hashing.store_image_tags(missing_file, [("nature", 0.9)])
    missing_file.unlink()

    present_file = temp_dir / "present.png"
    present_file.write_text("image data")
    _insert_hash(hash_db, "u2", present_file.as_posix())

    monkeypatch.setattr(
        tagging, "tag_file", lambda filename, top_k=5, threshold=None: [("city", 0.8)]
    )

    hashing.tag_wallpapers(clean=True)

    assert hashing.get_hashed_filenames() == {present_file.as_posix()}
    matches = hashing.search_image_tags(["city"])
    assert matches and matches[0][0] == present_file.as_posix()
    assert hashing.search_image_tags(["nature"]) == []


def test_get_all_tags(hash_db):
    _insert_hash(hash_db, "u1", "/tmp/img1.jpg")
    hashing.store_image_tags(Path("/tmp/img1.jpg"), [("cyberpunk", 0.8), ("city", 0.6)])

    assert hashing.get_all_tags() == {"cyberpunk", "city"}


def test_search_image_tags_matches_all_required_tags(hash_db):
    _insert_hash(hash_db, "u1", "/tmp/cyber1.jpg")
    _insert_hash(hash_db, "u2", "/tmp/cyber2.jpg")
    hashing.store_image_tags(
        Path("/tmp/cyber1.jpg"), [("cyberpunk", 0.8), ("city", 0.6), ("night", 0.9)]
    )
    hashing.store_image_tags(Path("/tmp/cyber2.jpg"), [("cyberpunk", 0.7)])

    only_cyber = hashing.search_image_tags(["cyberpunk"])
    cyber_city = hashing.search_image_tags(["cyberpunk", "city"])

    assert [f for f, _ in only_cyber] == ["/tmp/cyber1.jpg", "/tmp/cyber2.jpg"]
    assert [f for f, _ in cyber_city] == ["/tmp/cyber1.jpg"]
    assert dict(cyber_city[0][1]) == {"cyberpunk": 0.8, "city": 0.6}


def test_search_image_tags_deduplicates_and_returns_empty(hash_db):
    _insert_hash(hash_db, "u1", "/tmp/img1.jpg")
    hashing.store_image_tags(Path("/tmp/img1.jpg"), [("cyberpunk", 0.8)])

    dupes = hashing.search_image_tags(["cyberpunk", "cyberpunk"])
    assert len(dupes) == 1

    assert hashing.search_image_tags([]) == []
    assert hashing.search_image_tags(["does-not-exist"]) == []


def test_wpsearch_finds_images_by_tag(hash_db):
    _insert_hash(hash_db, "u1", "/tmp/cyber1.jpg")
    hashing.store_image_tags(
        Path("/tmp/cyber1.jpg"), [("cyberpunk", 0.8), ("city", 0.6)]
    )

    result = CliRunner().invoke(wpsearch, ["tag:cyberpunk"])

    assert result.exit_code == 0
    assert "/tmp/cyber1.jpg" in result.output
    assert "cyberpunk (0.80)" in result.output


def test_wpsearch_quoted_phrase_requires_all_tags(hash_db):
    _insert_hash(hash_db, "u1", "/tmp/a.jpg")
    _insert_hash(hash_db, "u2", "/tmp/b.jpg")
    hashing.store_image_tags(Path("/tmp/a.jpg"), [("cyberpunk", 0.8), ("city", 0.6)])
    hashing.store_image_tags(Path("/tmp/b.jpg"), [("cyberpunk", 0.7)])

    result = CliRunner().invoke(wpsearch, ["tag:cyberpunk city"])

    assert result.exit_code == 0
    assert "/tmp/a.jpg" in result.output
    assert "/tmp/b.jpg" not in result.output


def test_wpsearch_prefers_exact_multiword_tag(hash_db):
    _insert_hash(hash_db, "u1", "/tmp/a.jpg")
    hashing.store_image_tags(Path("/tmp/a.jpg"), [("science fiction", 0.8)])

    result = CliRunner().invoke(wpsearch, ["tag:science fiction"])

    assert result.exit_code == 0
    assert "/tmp/a.jpg" in result.output


def test_wpsearch_warns_on_unknown_tag(hash_db):
    records: list[str] = []
    handler = logging.Handler()
    handler.emit = lambda record: records.append(record.getMessage())
    logger = logging.getLogger("wpsrt")
    logger.addHandler(handler)
    try:
        result = CliRunner().invoke(wpsearch, ["tag:cyberpunk"])
    finally:
        logger.removeHandler(handler)

    assert result.exit_code == 0
    assert any("not found in database" in r for r in records)
    assert "Found 0 matching image(s)" in result.output


def test_wpsearch_rejects_non_tag_filter(hash_db):
    result = CliRunner().invoke(wpsearch, ["landscape"])

    assert result.exit_code == 2


def test_wpsearch_respects_limit(hash_db):
    _insert_hash(hash_db, "u1", "/tmp/a.jpg")
    _insert_hash(hash_db, "u2", "/tmp/b.jpg")
    hashing.store_image_tags(Path("/tmp/a.jpg"), [("cyberpunk", 0.8)])
    hashing.store_image_tags(Path("/tmp/b.jpg"), [("cyberpunk", 0.7)])

    result = CliRunner().invoke(wpsearch, ["tag:cyberpunk", "--limit", "1"])

    matches = [
        line for line in result.output.splitlines() if line.startswith("  /tmp/")
    ]
    assert len(matches) == 1
