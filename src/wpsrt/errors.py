from __future__ import annotations

from typing import final


@final
class SkipUnsupportedImage(Exception):
    _count: int = 0

    def __init__(self, message: str = "Unsupported image format") -> None:
        self.message = message
        SkipUnsupportedImage._count += 1
        super().__init__(self.message)

    @classmethod
    def count(cls) -> int:
        return cls._count

    @classmethod
    def reset_count(cls) -> None:
        cls._count = 0


class UnknownSortMethod(Exception):
    pass
