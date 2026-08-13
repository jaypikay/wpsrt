import enum
import sqlite3
from itertools import combinations
from pathlib import Path
from sys import stderr
from uuid import uuid4

import click
import imagehash
from imagehash import ImageHash, hex_to_flathash, hex_to_hash
from PIL import Image, UnidentifiedImageError
from xdg_base_dirs import xdg_data_home

from wpsrt.errors import SkipUnsupportedImage
from wpsrt.wallpapers import scan_directory

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
    global database_connection

    if database_connection:
        return database_connection

    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True)

    if not DB_FILE.exists():
        click.echo("Initializing image hash database...")

    database_connection = sqlite3.connect(database=DB_FILE)
    _ = database_connection.executescript(SCHEMA_HASHES)
    return database_connection


def store_hash(
    filename: Path,
    hashes: tuple[
        ImageHash,
        ImageHash,
        ImageHash,
        ImageHash,
    ],
    resolution: tuple[int, int],
):
    phash, dhash, colorhash, average_hash = hashes
    xres, yres = resolution

    db_con = init_hashdb()
    cur = db_con.cursor()
    data = [
        (
            str(uuid4()),
            filename.as_posix(),
            str(phash),
            str(dhash),
            str(colorhash),
            str(average_hash),
            xres,
            yres,
        ),
    ]
    _ = cur.executemany("""INSERT INTO hashes VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", data)
    db_con.commit()


def is_hashed(filename: Path) -> bool:
    db_con = init_hashdb()
    cur = db_con.cursor()
    res = cur.execute(
        """SELECT filename FROM hashes WHERE filename=?""", (filename.as_posix(),)
    )
    return res.fetchone() is not None


def fetch_hash(filename: Path):
    db_con = init_hashdb()
    cur = db_con.cursor()
    res = cur.execute(
        """SELECT filename, phash, dhash, colorhash, average_hash, xres, yres FROM hashes WHERE filename=?""",
        (filename.as_posix(),),
    )
    row = res.fetchone()
    if row is None:
        return None
    filename, phash, dhash, color, average, xres, yres = row  # pyright: ignore[reportAny]
    return (filename, phash, dhash, color, average, (xres, yres))


def cleanup_hashes():
    db_con = init_hashdb()
    cur = db_con.cursor()
    res = cur.execute("""SELECT uuid, filename FROM hashes""")
    for row in res.fetchall():
        uuid = row[0]
        filename = Path(row[1])
        if not filename.exists():
            click.secho(f"File not found: {filename}", fg="red")
            res = cur.execute("""DELETE FROM hashes WHERE uuid=?""", (uuid,))
    db_con.commit()


def fetch_hashes():
    db_con = init_hashdb()
    cur = db_con.cursor()
    res = cur.execute(
        """SELECT filename, phash, dhash, colorhash, average_hash, xres, yres FROM hashes"""
    )
    return res.fetchall()


def hash_wallpapers(target: Path):
    """
    Scans a directory for images, calculates their perceptual hashes (phash),
    and prints this information.

    This function is useful for identifying potential duplicate images by comparing
    their hash values. It prints the phash, resolution (formatted as 'WIDTHxHEIGHT'),
    and filename for each image. Example: `d8e8c0c0c0c0e0e0 1920x1080 /path/to/image.jpg`

    Args:
        target: The Path object of the directory to scan for wallpapers.

    Returns:
        A list of tuples, where each tuple contains:
            - filename (Path): The path to the image file.
            - phash (imagehash.ImageHash): The perceptual hash of the image.
            - image (ImageFile.ImageFile): The PIL Image object.
    """

    _ = init_hashdb()

    click.echo(f"Hashing wallpaper {target}...")
    if target.is_file():
        found_files = [target]
    else:
        found_files = list(scan_directory(target))  # Collect all wallpapers first
    new_hash_count = 0
    with click.progressbar(found_files, label="Hashing wallpapers") as progress:
        for filename in progress:
            try:
                if not is_hashed(filename):
                    with Image.open(filename) as image:
                        phash = imagehash.phash(image)
                        dhash = imagehash.dhash(image)
                        color = imagehash.colorhash(image)
                        average = imagehash.average_hash(image)  # pyright: ignore[reportUnknownMemberType]

                        store_hash(filename, (phash, dhash, color, average), image.size)
                        new_hash_count += 1
                else:
                    filename, phash, dhash, color, average, _image_size = fetch_hash(  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                        filename
                    )

            except UnidentifiedImageError as e:
                try:
                    raise SkipUnsupportedImage
                except SkipUnsupportedImage:
                    click.secho(f"Error hashing {filename}: {e}", err=True, fg="red")
                continue

    click.echo(f"Added {new_hash_count} images to hash database")


def compare_hashes(hash: str, threshold: int = 5, output: Path | None = None):
    hashes = fetch_hashes()

    hashcol = HashColumn.__getitem__(hash).value

    hashlist = []
    with click.progressbar(
        hashes, label="Preparing hash list", file=stderr
    ) as progress:
        for row in progress:
            if hash == "colorhash":
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
        with open(output, "tw", encoding="utf-8") as fd:
            click.echo(f"Found {len(results)} possible similar images.", file=stderr)
            for a_file, b_file, distance in sorted(results, key=lambda e: e[2]):
                click.echo(
                    f"hash={hash};distance={distance};{a_file[0]};{b_file[0]}", file=fd
                )