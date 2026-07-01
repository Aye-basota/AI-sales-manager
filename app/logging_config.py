"""Centralized logging configuration for production observability."""

from __future__ import annotations

import logging
import sys
from typing import Any


def configure_logging(level: int | str | None = None) -> dict[str, Any]:
    """Return a dict-config compatible logging configuration.

    Logs are written to stderr in a structured-ish plain-text format suitable
    for containerized deployments. The same format works with ``docker logs``
    and common log shippers (e.g. journald, Vector, Fluent Bit).
    """
    if level is None:
        level = logging.INFO

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "stderr": {
                "class": "logging.StreamHandler",
                "stream": sys.stderr,
                "formatter": "default",
            },
        },
        "root": {
            "level": level,
            "handlers": ["stderr"],
        },
        "loggers": {
            # ``propagate`` is intentionally left at the default (True) so test
            # fixtures such as pytest's ``caplog`` can capture application logs.
            "app": {"level": level, "handlers": ["stderr"]},
            "uvicorn": {"level": level, "handlers": ["stderr"], "propagate": False},
            "uvicorn.access": {"level": level, "handlers": ["stderr"], "propagate": False},
        },
    }


def setup_logging(level: int | str | None = None) -> None:
    """Apply the logging configuration."""
    import logging.config

    logging.config.dictConfig(configure_logging(level))
