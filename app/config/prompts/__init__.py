"""Prompt configuration loader.

Prompts are stored outside application source code (TECH-13) so that prompt
versions can be updated without modifying business logic.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_PROMPT_CONFIG_PATH = Path(__file__).parent / "v1.json"


@lru_cache()
def load_prompt_config(path: Path | str | None = None) -> dict[str, Any]:
    """Load the prompt configuration from a JSON file.

    The path defaults to ``app/config/prompts/v1.json``. The result is cached
    for the lifetime of the process.
    """
    config_path = Path(path) if path else DEFAULT_PROMPT_CONFIG_PATH
    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error("Prompt config not found at %s", config_path)
        raise
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in prompt config %s: %s", config_path, exc)
        raise

    logger.debug("Loaded prompt config version %s from %s", config.get("version"), config_path)
    return config


def get_prompt_config_version(config: dict[str, Any] | None = None) -> str:
    """Return the version of the loaded prompt config."""
    cfg = config or load_prompt_config()
    return cfg.get("version", "unknown")
