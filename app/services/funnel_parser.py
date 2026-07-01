"""Parsers for funnel definition files (JSON and plain text)."""

from __future__ import annotations

import json
import re
from typing import Any


class FunnelParseError(ValueError):
    """Raised when a funnel definition cannot be parsed or validated."""

    pass


def _validate_stages(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate and normalize a list of funnel stages."""
    if not isinstance(stages, list):
        raise FunnelParseError("Funnel stages must be a list.")
    if len(stages) == 0:
        raise FunnelParseError("Funnel must contain at least one stage.")

    normalized: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for idx, raw in enumerate(stages, start=1):
        if not isinstance(raw, dict):
            raise FunnelParseError(f"Stage {idx} must be an object.")
        stage = raw.get("stage") or raw.get("name")
        if not stage:
            raise FunnelParseError(f"Stage {idx} is missing a 'stage' or 'name' field.")
        if stage in seen_names:
            raise FunnelParseError(f"Duplicate stage name: {stage}.")
        seen_names.add(stage)

        normalized.append(
            {
                "stage": str(stage),
                "goal": str(raw.get("goal", "")),
                "instructions": str(raw.get("instructions", "")),
                "max_length": int(raw.get("max_length", 400)) if raw.get("max_length") is not None else 400,
                "allow_call_to_action": bool(raw.get("allow_call_to_action", False)),
            }
        )
    return normalized


def parse_funnel_json(content: str) -> list[dict[str, Any]]:
    """Parse a JSON funnel definition."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise FunnelParseError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise FunnelParseError("JSON root must be an object.")

    stages = data.get("stages")
    if stages is None:
        raise FunnelParseError("Missing 'stages' field in JSON.")

    return _validate_stages(stages)


def parse_funnel_text(content: str) -> list[dict[str, Any]]:
    """Parse a plain-text funnel definition using '## Stage N' headings."""
    lines = content.splitlines()
    stages: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_body: list[str] = []

    heading_re = re.compile(r"^##\s*(.+)$")

    def _flush() -> None:
        nonlocal current, current_body
        if current is not None:
            body = "\n".join(current_body).strip()
            current["instructions"] = body
            stages.append(current)
            current = None
            current_body = []

    for line in lines:
        match = heading_re.match(line.strip())
        if match:
            _flush()
            stage_name = match.group(1).strip()
            # Remove a numeric prefix like "Stage 1: ..."
            stage_name = re.sub(r"^Stage\s+\d+[:.\-]?\s*", "", stage_name, flags=re.IGNORECASE)
            current = {
                "stage": stage_name,
                "goal": "",
                "instructions": "",
                "max_length": 400,
                "allow_call_to_action": False,
            }
        elif current is not None:
            current_body.append(line)

    _flush()

    return _validate_stages(stages)


def parse_funnel(content: str, fmt: str) -> list[dict[str, Any]]:
    """Parse funnel content in the requested format."""
    fmt = fmt.lower().strip()
    if fmt == "json":
        return parse_funnel_json(content)
    if fmt == "text":
        return parse_funnel_text(content)
    raise FunnelParseError(f"Unsupported format: {fmt}. Use 'json' or 'text'.")
