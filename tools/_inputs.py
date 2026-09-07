"""Validate tool inputs before sending a request to Asqav."""
import json
import re
from typing import Any


def required_text(values: dict[str, Any], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        label = {"asqav_api_key": "Asqav API key", "asqav_agent_id": "Agent ID"}.get(key, key)
        raise ValueError(f"{label} must be a non-empty string")
    return value


def path_identifier(values: dict[str, Any], key: str) -> str:
    value = required_text(values, key)
    if re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
        raise ValueError(f"{key} must contain only letters, digits, underscores or hyphens")
    return value


def object_parameter(values: dict[str, Any], key: str) -> dict[str, Any]:
    value = values.get(key)
    if value is None or value == "":
        return {}
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a JSON object encoded as a string")
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {"raw": value}
    if not isinstance(parsed, dict):
        raise ValueError(f"{key} must be a JSON object; arrays and scalar values are unsupported")
    return parsed
