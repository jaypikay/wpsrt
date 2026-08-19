"""Structured logging setup for wpsrt.

All wpsrt loggers are children of the ``wpsrt`` logger, which is configured
by :func:`setup_logging` to write to a rotating log file. By default the log
file lives at ``~/.local/var/log/wpsrt.log``.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

LOGGER_NAME = "wpsrt"
DEFAULT_LOG_DIR = Path("~/.local/var/log").expanduser()
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "wpsrt.log"
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3


def setup_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
    force: bool = False,
) -> Path:
    """Configures structured file logging for the wpsrt application.

    Log records emitted by any ``wpsrt.*`` logger are written to a rotating
    log file. Calling this function more than once is a no-op unless
    ``force`` is set, which allows reconfiguration (mainly useful in tests).

    Args:
        level: The minimum logging level to capture.
        log_file: Optional override for the log file path.
        force: If True, reconfigure logging even if already configured.

    Returns:
        The path to the log file being written to.
    """
    target_file = log_file if log_file is not None else DEFAULT_LOG_FILE
    logger = logging.getLogger(LOGGER_NAME)

    if logger.handlers and not force:
        return target_file

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    target_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.handlers.RotatingFileHandler(
        target_file, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False

    return target_file
