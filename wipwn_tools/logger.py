"""Logging setup for wipwn v2."""

from __future__ import annotations

import logging
import os
from pathlib import Path


def log_dir() -> Path:
    home = Path(os.environ.get("HOME", Path.home()))
    return home / ".wipwn" / "logs"


def setup_logging(verbose: bool = False, log_file: str | None = None) -> logging.Logger:
    directory = log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = Path(log_file) if log_file else directory / "wipwn.log"

    logger = logging.getLogger("wipwn")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console)

    logger.propagate = False
    return logger
