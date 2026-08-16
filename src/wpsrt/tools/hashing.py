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

DATA_DIR = xdg_data_home() / "wpsrt"
DB_FILE = DATA_DIR / "hashdb.sqlite"


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
        click.echo("Initializing image hash database...")
        logger.info("Initializing image hash database at %s", DB_FILE)

    database_connection = sqlite3.connect(database=DB_FILE)
    _ = database_connection.executescript(SCHEMA_HASHES)
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
            click.secho(f"File not found: {fname}", fg="red")
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


def hash_wallpapers(target: Path) -> None:
    """Scans a directory for images, calculates perceptual hashes, and stores them in DB."""
    _ = init_hashdb()

    click.echo(f"Hashing wallpaper {target}...")
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
                    click.secho(f"Error hashing {filename}: {e}", err=True, fg="red")
                    logger.warning("Error hashing %s: %s", filename, e)
                    continue

    if pending_records:
        store_hashes_batch(pending_records)

    click.echo(f"Added {new_hash_count} images to hash database")


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
            click.echo(f"Found {len(results)} possible similar images.", file=stderr)
            for a_file, b_file, distance in sorted(results, key=lambda e: e[2]):
                click.echo(
                    f"hash={hash_method};distance={distance};{a_file[0]};{b_file[0]}",
                    file=fd,
                )
        logger.info("Wrote %d similarity result(s) to %s", len(results), output)
