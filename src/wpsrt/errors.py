from typing_extensions import final


NumberSkippedImages = 0


@final
class SkipUnsupportedImage(Exception):
    def __init__(self, message: str = "Unsupported image format"):
        global NumberSkippedImages
        self.message = message
        NumberSkippedImages += 1
        super().__init__(self.message)

    @staticmethod
    def count() -> int:
        global NumberSkippedImages
        return NumberSkippedImages


class UnknownSortMethod(Exception):
    pass