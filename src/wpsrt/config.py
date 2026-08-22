from dataclasses import dataclass, field


@dataclass
class Config:
    """Configuration for the WPSRT application."""

    # General settings
    log_level: str = field(default="INFO", metadata={"help": "Logging level"})

    sorting_algorithm: str = field(
        default="clip",
        metadata={"help": "Sorting algorithm to use (e.g., 'clip', 'color', etc.)"},
    )

    # Other settings can be added here as needed
    clip_threshold: float = field(
        default=0.8, metadata={"help": "CLIP score threshold"}
    )

    source_directory: str = field(
        default="~/Pictures/wallpapers/",
        metadata={"help": "Directory containing source images"},
    )
    target_directory: str = field(
        default="~/Pictures/Wallpapers/",
        metadata={"help": "Directory containing sorted images"},
    )