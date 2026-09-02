from __future__ import annotations

import enum
import logging
import sqlite3
from itertools import combinations
from pathlib import Path
from sys import stderr
from typing import Any
from uuid import uuid4

import click
import imagehash
from imagehash import ImageHash, hex_to_flathash, hex_to_hash
from PIL import Image, UnidentifiedImageError
from xdg_base_dirs import xdg_data_home

from wpsrt.config import Config
from wpsrt.wallpapers import scan_directory

logger = logging.getLogger(__name__)

SCHEMA_HASHES = """CREATE TABLE IF NOT EXISTS hashes (
    uuid PRIMARY KEY,
    filename TEXT NOT NULL UNIQUE,
    phash TEXT NOT NULL,
    dhash TEXT NOT NULL,
    colorhash TEXT NOT NULL,
    average_hash TEXT NOT NULL,
    xres INT NOT NULL,
    yres INT NOT NULL
);
CREATE INDEX IF NOT EXISTS phash ON hashes(phash);
CREATE INDEX IF NOT EXISTS dhash ON hashes(dhash);
CREATE INDEX IF NOT EXISTS colorhash ON hashes(colorhash);
CREATE INDEX IF NOT EXISTS average_hash ON hashes(average_hash);
CREATE INDEX IF NOT EXISTS filename ON hashes(filename);
"""

SCHEMA_TAGS = """CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS image_tags (
    image_uuid TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    confidence REAL NOT NULL,
    PRIMARY KEY (image_uuid, tag_id),
    FOREIGN KEY (image_uuid) REFERENCES hashes(uuid) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_image_tags_tag_id ON image_tags(tag_id);
"""

DATA_DIR = xdg_data_home() / "wpsrt"
DB_FILE = DATA_DIR / "wpsrt.sqlite"


class HashColumn(enum.Enum):
    phash = 1
    dhash = 2
    colorhash = 3
    average_hash = 4


database_connection: sqlite3.Connection | None = None


def init_hashdb() -> sqlite3.Connection:
    """Initializes and returns the SQLite database connection."""
    global database_connection

    if database_connection:
        return database_connection

    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not DB_FILE.exists():
        logger.info("Initializing image hash database at %s", DB_FILE)

    database_connection = sqlite3.connect(database=DB_FILE)
    database_connection.execute("PRAGMA foreign_keys = ON")
    _ = database_connection.executescript(SCHEMA_HASHES)
    _ = database_connection.executescript(SCHEMA_TAGS)
    return database_connection


def store_hashes_batch(
    records: list[tuple[str, str, str, str, str, str, int, int]],
) -> None:
    """Stores multiple hash records into the database in a single transaction."""
    if not records:
        return
    db_con = init_hashdb()
    cur = db_con.cursor()
    _ = cur.executemany(
        """INSERT INTO hashes VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", records
    )
    db_con.commit()


def store_hash(
    filename: Path,
    hashes: tuple[
        ImageHash,
        ImageHash,
        ImageHash,
        ImageHash,
    ],
    resolution: tuple[int, int],
) -> None:
    """Stores a single image hash entry into the database."""
    phash, dhash, colorhash, average_hash = hashes
    xres, yres = resolution
    store_hashes_batch(
        [
            (
                str(uuid4()),
                filename.as_posix(),
                str(phash),
                str(dhash),
                str(colorhash),
                str(average_hash),
                xres,
                yres,
            )
        ]
    )


def get_hashed_filenames() -> set[str]:
    """Returns a set of all filenames already present in the database."""
    db_con = init_hashdb()
    cur = db_con.cursor()
    res = cur.execute("""SELECT filename FROM hashes""")
    return {row[0] for row in res.fetchall()}


def is_hashed(filename: Path) -> bool:
    """Checks whether a single file is present in the hash database."""
    db_con = init_hashdb()
    cur = db_con.cursor()
    res = cur.execute(
        """SELECT filename FROM hashes WHERE filename=?""", (filename.as_posix(),)
    )
    return res.fetchone() is not None


def fetch_hash(
    filename: Path,
) -> tuple[str, str, str, str, str, tuple[int, int]] | None:
    """Fetches hash details for a specific filename."""
    db_con = init_hashdb()
    cur = db_con.cursor()
    res = cur.execute(
        """SELECT filename, phash, dhash, colorhash, average_hash, xres, yres FROM hashes WHERE filename=?""",
        (filename.as_posix(),),
    )
    row = res.fetchone()
    if row is None:
        return None
    fname, phash, dhash, color, average, xres, yres = row
    return (fname, phash, dhash, color, average, (xres, yres))


def cleanup_hashes() -> None:
    """Removes hash database entries for files that no longer exist."""
    db_con = init_hashdb()
    cur = db_con.cursor()
    res = cur.execute("""SELECT uuid, filename FROM hashes""")
    missing_uuids = []
    for row in res.fetchall():
        uuid, fname = row[0], Path(row[1])
        if not fname.exists():
            logger.warning("Removing hash entry for missing file: %s", fname)
            missing_uuids.append((uuid,))
    if missing_uuids:
        cur.executemany("""DELETE FROM hashes WHERE uuid=?""", missing_uuids)
        db_con.commit()
        logger.info("Removed %d stale hash entries", len(missing_uuids))


def fetch_hashes() -> list[tuple[Any, ...]]:
    """Retrieves all hash records from the database."""
    db_con = init_hashdb()
    cur = db_con.cursor()
    res = cur.execute(
        """SELECT filename, phash, dhash, colorhash, average_hash, xres, yres FROM hashes"""
    )
    return res.fetchall()


def store_image_tags(filename: Path, tags: list[tuple[str, float]]) -> None:
    """Stores tags for a single hashed image, upserting tag rows and links.

    Args:
        filename: The image path as recorded in the hash database.
        tags: Iterable of ``(tag_name, confidence)`` tuples.
    """
    if not tags:
        return
    db_con = init_hashdb()
    cur = db_con.cursor()
    row = cur.execute(
        "SELECT uuid FROM hashes WHERE filename=?", (filename.as_posix(),)
    ).fetchone()
    if row is None:
        logger.warning("Cannot store tags for unhashed image: %s", filename)
        return
    image_uuid = row[0]
    for tag, confidence in tags:
        cur.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (tag,))
        tag_id = cur.execute("SELECT id FROM tags WHERE name=?", (tag,)).fetchone()[0]
        cur.execute(
            """INSERT INTO image_tags (image_uuid, tag_id, confidence)
               VALUES (?, ?, ?)
               ON CONFLICT (image_uuid, tag_id)
               DO UPDATE SET confidence=excluded.confidence""",
            (image_uuid, tag_id, confidence),
        )
    db_con.commit()


def clear_image_tags(filename: Path) -> None:
    """Removes all stored tags for a single image.

    Args:
        filename: The image path as recorded in the hash database.
    """
    db_con = init_hashdb()
    cur = db_con.cursor()
    row = cur.execute(
        "SELECT uuid FROM hashes WHERE filename=?", (filename.as_posix(),)
    ).fetchone()
    if row is None:
        return
    cur.execute("DELETE FROM image_tags WHERE image_uuid=?", (row[0],))
    db_con.commit()


def get_tagged_filenames() -> set[str]:
    """Returns filenames in the hash database that already have at least one tag."""
    db_con = init_hashdb()
    cur = db_con.cursor()
    res = cur.execute(
        """SELECT h.filename
           FROM image_tags it
           JOIN hashes h ON h.uuid = it.image_uuid"""
    )
    return {row[0] for row in res.fetchall()}


def fetch_untagged_filenames() -> list[Path]:
    """Returns paths of hashed images that have no tags stored yet."""
    db_con = init_hashdb()
    cur = db_con.cursor()
    res = cur.execute(
        """SELECT h.filename
           FROM hashes h
           LEFT JOIN image_tags it ON it.image_uuid = h.uuid
           WHERE it.image_uuid IS NULL
           ORDER BY h.filename"""
    )
    return [Path(row[0]) for row in res.fetchall()]


def get_all_tags() -> set[str]:
    """Returns the name of every tag currently stored in the database."""
    db_con = init_hashdb()
    cur = db_con.cursor()
    rows = cur.execute("SELECT name FROM tags").fetchall()
    return {row[0] for row in rows}


def list_tags() -> list[tuple[str, int]]:
    """Returns every used tag with the number of images it is assigned to.

    Returns:
        A list of ``(tag_name, count)`` tuples sorted by descending count,
        then alphabetically by tag name.
    """
    db_con = init_hashdb()
    cur = db_con.cursor()
    rows = cur.execute(
        """SELECT t.name, COUNT(it.image_uuid) AS cnt
           FROM tags t
           JOIN image_tags it ON it.tag_id = t.id
           GROUP BY t.id, t.name
           ORDER BY cnt DESC, t.name"""
    ).fetchall()
    return [(name, count) for name, count in rows]


def search_image_tags(
    tag_names: list[str],
) -> list[tuple[str, list[tuple[str, float]]]]:
    """Returns hashed images tagged with all of the given tag names.

    Args:
        tag_names: Tag names that must all be assigned to an image.

    Returns:
        A list of ``(filename, tags)`` tuples sorted by filename, where
        ``tags`` maps each requested tag to its stored confidence.
    """
    required = list(dict.fromkeys(tag_names))
    if not required:
        return []
    placeholders = ",".join("?" for _ in required)
    db_con = init_hashdb()
    cur = db_con.cursor()
    rows = cur.execute(
        f"""SELECT h.filename, t.name, it.confidence
            FROM image_tags it
            JOIN tags t ON t.id = it.tag_id
            JOIN hashes h ON h.uuid = it.image_uuid
            WHERE t.name IN ({placeholders})""",
        required,
    ).fetchall()
    per_file: dict[str, dict[str, float]] = {}
    for filename, tag, confidence in rows:
        per_file.setdefault(filename, {})[tag] = confidence
    required_set = set(required)
    results = [
        (
            filename,
            [(tag, conf) for tag, conf in assignments.items() if tag in required_set],
        )
        for filename, assignments in per_file.items()
        if required_set <= assignments.keys()
    ]
    return sorted(results, key=lambda item: item[0])


def hash_wallpapers(target: Path) -> None:
    """Scans a directory for images, calculates perceptual hashes, and stores them in DB."""
    _ = init_hashdb()

    logger.info("Hashing wallpapers in %s", target)
    if target.is_file():
        found_files = [target]
    else:
        found_files = list(scan_directory(target))

    existing_hashes = get_hashed_filenames()
    pending_records: list[tuple[str, str, str, str, str, str, int, int]] = []
    new_hash_count = 0

    with click.progressbar(found_files, label="Hashing wallpapers") as progress:
        for filename in progress:
            posix_path = filename.as_posix()
            if posix_path not in existing_hashes:
                try:
                    with Image.open(filename) as image:
                        phash = imagehash.phash(image)
                        dhash = imagehash.dhash(image)
                        color = imagehash.colorhash(image)
                        average = imagehash.average_hash(image)
                        xres, yres = image.size

                    pending_records.append(
                        (
                            str(uuid4()),
                            posix_path,
                            str(phash),
                            str(dhash),
                            str(color),
                            str(average),
                            xres,
                            yres,
                        )
                    )
                    existing_hashes.add(posix_path)
                    new_hash_count += 1

                    if len(pending_records) >= 100:
                        store_hashes_batch(pending_records)
                        pending_records.clear()
                except UnidentifiedImageError as e:
                    logger.warning("Error hashing %s: %s", filename, e)
                    continue

    if pending_records:
        store_hashes_batch(pending_records)

    logger.info("Added %d images to hash database", new_hash_count)


def compare_hashes(
    hash_method: str, threshold: int = 5, output: Path | None = None
) -> None:
    """Compares stored hashes and outputs potential duplicates based on threshold."""
    hashes = fetch_hashes()
    hashcol = HashColumn[hash_method].value
    logger.info(
        "Comparing %d hash(es) using %s (threshold=%d)",
        len(hashes),
        hash_method,
        threshold,
    )

    hashlist = []
    with click.progressbar(
        hashes, label="Preparing hash list", file=stderr
    ) as progress:
        for row in progress:
            if hash_method == "colorhash":
                hashval = hex_to_flathash(row[hashcol], 7)
            else:
                hashval = hex_to_hash(row[hashcol])

            hashlist.append((row[0], hashval, (row[5], row[6])))

    results = []
    with click.progressbar(
        combinations(hashlist, 2),
        label="Checking hash similarities",
        file=stderr,
        show_eta=True,
    ) as progress:
        for img_a, img_b in progress:
            distance = img_a[1] - img_b[1]
            if distance <= threshold:
                results.append(
                    ((img_a[0], img_a[-2:]), (img_b[0], img_b[-2:]), distance)
                )
                click.echo(img_a[0])
                click.echo(img_b[0])

    if output:
        with open(output, "w", encoding="utf-8") as fd:
            logger.info("Found %d possible similar images.", len(results))
            for a_file, b_file, distance in sorted(results, key=lambda e: e[2]):
                click.echo(
                    f"hash={hash_method};distance={distance};{a_file[0]};{b_file[0]}",
                    file=fd,
                )
        logger.info("Wrote %d similarity result(s) to %s", len(results), output)


def tag_wallpapers(
    top_k: int = 5,
    refresh: bool = False,
    threshold: float | None = None,
    clean: bool = False,
) -> None:
    """Tags images in the hash database using the CLIP vision model.

    By default only untagged images are processed; previously tagged images are
    left untouched. With ``refresh=True`` every image is re-tagged and its
    previously stored tags are replaced by the current predictions.

    An image is only tagged when at least one predicted tag reaches
    ``threshold``; images where every tag falls below it are skipped without
    storing anything.

    Args:
        top_k: Number of tags to assign per image.
        refresh: If True, re-tag all images, replacing existing tags.
        threshold: Minimum confidence required for a tag to be stored. Defaults
            to ``Config.tagging_threshold`` when None.
        clean: If True, first remove hash entries (and their tags) for images
            that can no longer be accessed on the filesystem.
    """
    _ = init_hashdb()
    from wpsrt.errors import SkipUnsupportedImage
    from wpsrt.methods import tagging

    if clean:
        cleanup_hashes()

    if threshold is None:
        threshold = Config.tagging_threshold

    candidates = (
        sorted(Path(fname) for fname in get_hashed_filenames())
        if refresh
        else fetch_untagged_filenames()
    )
    logger.info(
        "Tagging %d image(s), refresh=%s threshold=%0.2f",
        len(candidates),
        refresh,
        threshold,
    )
    tagged_count = 0
    skip_count = 0
    below_threshold_count = 0

    with click.progressbar(candidates, label="Tagging images") as progress:
        for filename in progress:
            try:
                tags = tagging.tag_file(filename, top_k=top_k, threshold=threshold)
                if not tags:
                    logger.debug(
                        "Skipping %s: no tag above CLIP threshold (%0.2f)",
                        filename,
                        threshold,
                    )
                    below_threshold_count += 1
                    continue
                if refresh:
                    clear_image_tags(filename)
                store_image_tags(filename, tags)
                tagged_count += 1
            except SkipUnsupportedImage:
                skip_count += 1
                continue

    logger.info(
        "Finished tagging: tagged=%d skipped=%d below_threshold=%d",
        tagged_count,
        skip_count,
        below_threshold_count,
    )