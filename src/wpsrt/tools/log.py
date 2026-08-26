"""Structured logging setup for wpsrt.

All wpsrt loggers are children of the ``wpsrt`` logger, which is configured
by :func:`setup_logging` to write to a rotating log file (by default at
``~/.local/var/log/wpsrt.log``). Only error-level records (and above) are
echoed to the console; everything else goes to the log file only.
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
    """Configures structured logging for the wpsrt application.

    Log records emitted by any ``wpsrt.*`` logger are written to a rotating
    log file. A console handler echoes only records at ``ERROR`` level or
    above; informational and warning records appear solely in the log file.
    Calling this function more than once is a no-op unless ``force`` is set,
    which allows reconfiguration (mainly useful in tests).

    Args:
        level: The minimum logging level to capture in the log file.
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

    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.handlers.RotatingFileHandler(
        target_file, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.propagate = False

    return target_file
