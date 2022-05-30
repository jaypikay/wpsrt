import pathlib
from typing import Iterable

from PIL import Image


def scan_directory(directory: pathlib.Path) -> Iterable[pathlib.Path]:
    for filename in directory.iterdir():
        if filename.is_file():
            image = Image.open(filename)
            print(image.size)
            yield filename
