from __future__ import annotations

import logging
from pathlib import Path

import pytest

from wpsrt.tools.log import setup_logging


def test_setup_logging_creates_log_file(temp_dir: Path):
    log_file = temp_dir / "wpsrt.log"
    logger_name = "wpsrt"

    result = setup_logging(log_file=log_file, force=True)

    assert result == log_file
    assert log_file.parent.exists()

    logger = logging.getLogger(logger_name)
    logger.info("test message")
    for handler in logger.handlers:
        handler.flush()

    assert log_file.exists()
    assert "test message" in log_file.read_text(encoding="utf-8")


def test_setup_logging_is_idempotent(temp_dir: Path):
    first_file = temp_dir / "first.log"
    second_file = temp_dir / "second.log"

    result_first = setup_logging(log_file=first_file, force=True)
    result_second = setup_logging(log_file=second_file)

    assert result_first == first_file
    assert result_second == second_file
    assert not second_file.exists()


def test_console_handler_only_echoes_errors(
    temp_dir: Path, capsys: pytest.CaptureFixture
):
    setup_logging(log_file=temp_dir / "wpsrt.log", force=True)
    logger = logging.getLogger("wpsrt")

    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    for handler in logger.handlers:
        handler.flush()

    captured = capsys.readouterr()
    assert "info message" not in captured.err
    assert "warning message" not in captured.err
    assert "error message" in captured.err


def test_non_error_records_still_go_to_log_file(temp_dir: Path):
    log_file = temp_dir / "wpsrt.log"
    setup_logging(log_file=log_file, force=True)
    logger = logging.getLogger("wpsrt")

    logger.info("info message")
    logger.warning("warning message")
    for handler in logger.handlers:
        handler.flush()

    content = log_file.read_text(encoding="utf-8")
    assert "info message" in content
    assert "warning message" in content
