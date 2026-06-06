import sqlite3
from pathlib import Path
from uuid import uuid4

import click
import imagehash
from PIL import Image
from xdg_base_dirs import xdg_data_home

from wpsrt.errors import SkipUnsupportedImage
from wpsrt.wallpapers import scan_directory

SCHEMA_HASHES = """CREATE TABLE IF NOT EXISTS hashes (
    uuid PRIMARY KEY,
    filename TEXT NOT NULL UNIQUE,
    p TEXT NOT NULL,
    d TEXT NOT NULL,
    color TEXT NOT NULL,
    average TEXT NOT NULL,
    xres INT NOT NULL,
    yres INT NOT NULL
);
CREATE INDEX IF NOT EXISTS phash ON hashes(p);
CREATE INDEX IF NOT EXISTS dhash ON hashes(d);
CREATE INDEX IF NOT EXISTS colorhash ON hashes(color);
CREATE INDEX IF NOT EXISTS average_hash ON hashes(average);
CREATE INDEX IF NOT EXISTS filename ON hashes(filename);
"""

DATA_DIR = xdg_data_home() / "wpsrt"
DB_FILE = DATA_DIR / "hashdb.sqlite"

db_con: sqlite3.Connection | None = None


def init_hashdb():
    global db_con

    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True)

    if not DB_FILE.exists():
        click.echo("Initializing image hash database...")
        db_con = sqlite3.connect(database=DB_FILE)
        cur = db_con.cursor()
        _ = cur.executescript(SCHEMA_HASHES)
    else:
        db_con = sqlite3.connect(database=DB_FILE)


def store_hash(
    filename: Path,
    hashes: tuple[
        imagehash.ImageHash,
        imagehash.ImageHash,
        imagehash.ImageHash,
        imagehash.ImageHash,
    ],
    resolution: tuple[int, int],
):
    global db_con

    phash, dhash, colorhash, average_hash = hashes
    xres, yres = resolution

    if not db_con:
        init_hashdb()
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
    global db_con

    if not db_con:
        init_hashdb()

    cur = db_con.cursor()
    res = cur.execute(
        """SELECT filename FROM hashes WHERE filename=?""", (filename.as_posix(),)
    )
    try:
        _ = res.fetchone()[0]
        return True
    except:
        return False


def fetch_hashes(filename: Path):
    global db_con

    if not db_con:
        init_hashdb()

    cur = db_con.cursor()
    res = cur.execute(
        """SELECT filename, p, d, color, average, xres, yres FROM hashes WHERE filename=?""",
        (filename.as_posix(),),
    )
    try:
        filename, phash, dhash, color, average, xres, yres = res.fetchone()
        return (filename, phash, dhash, color, average, (xres, yres))
    except:
        return None


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

    init_hashdb()

    click.echo(f"Hashing wallpaper {target}...")
    if target.is_file():
        found_files = [target]
    else:
        found_files = list(scan_directory(target))  # Collect all wallpapers first
    hashes: list[
        tuple[
            Path,
            tuple[
                imagehash.ImageHash,
                imagehash.ImageHash,
                imagehash.ImageHash,
                imagehash.ImageHash,
            ],
            tuple[int, int],
        ]
    ] = []
    with click.progressbar(found_files, label="Hashing wallpapers") as progress:
        for filename in progress:
            try:
                if not is_hashed(filename):
                    image = Image.open(filename)
                    phash = imagehash.phash(image)
                    dhash = imagehash.dhash(image)
                    color = imagehash.colorhash(image)
                    average = imagehash.average_hash(image)  # pyright: ignore[reportUnknownMemberType]

                    store_hash(filename, (phash, dhash, color, average), image.size)
                    hashes.append(
                        (filename, (phash, dhash, color, average), image.size)
                    )
                else:
                    filename, phash, dhash, color, average, image_size = fetch_hashes(
                        filename
                    )
                    hashes.append(
                        (filename, (phash, dhash, color, average), image_size)
                    )

            except SkipUnsupportedImage as e:
                click.secho(f"Error hashing {filename}: {e}", err=True, fg="red")
                continue

    # Output the collected hash information
    # This part might be refactored later if actual duplicate removal is implemented
    click.secho(
        """pHash            dHash            colorHash   average Hash       Resolution  Filename
=====            =====            =========   ============       ==========  ========"""
    )
    for filename, (phash, dhash, colorhash, average_hash), (xres, yres) in hashes:
        # Use click.echo for consistent output formatting
        click.echo(
            f"{phash} {dhash} {colorhash} {average_hash} {xres:6d}x{yres:<6d} {filename}"
        )

    # TODO store in database
