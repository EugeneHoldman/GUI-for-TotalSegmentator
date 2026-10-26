"""Logging helpers for the UI app.

Keep this module lightweight so import-time stays fast.
"""

from __future__ import annotations

import logging


def get_logger(name: str = "totalseg_ui") -> logging.Logger:
    """Return a logger with a NullHandler to avoid duplicate handlers."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger
