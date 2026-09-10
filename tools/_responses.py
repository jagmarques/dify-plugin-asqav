"""Validate upstream fields before exposing workflow outputs."""
from collections.abc import Sequence
import math
from typing import Any

FieldSpec = Sequence[tuple[str, str]]


def _finite_number(value: Any) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _usable(value: Any, kind: str) -> bool:
    if kind == "text":
        return isinstance(value, str) and bool(value.strip())
    if kind == "text_or_null":
        return value is None or isinstance(value, str)
    if kind == "object_or_null":
        return value is None or isinstance(value, dict)
    if kind == "number":
        return _finite_number(value)
    if kind in ("positive_integer", "nonnegative_integer"):
        minimum = 1 if kind == "positive_integer" else 0
        return type(value) is int and value >= minimum and _finite_number(value)
    if kind == "flag":
        return type(value) is bool
    raise ValueError(f"Unknown response field kind: {kind}")


def response_payload(data: Any, tool: str, fields: FieldSpec) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError(f"{tool}: expected a JSON object response")
    for name, kind in fields:
        if name not in data:
            raise ValueError(f"{tool}: response missing {name}")
        if not _usable(data[name], kind):
            raise ValueError(f"{tool}: invalid response field {name} (expected {kind})")
    return {name: data[name] for name, _ in fields}


def optional_text(data: dict[str, Any], name: str, tool: str) -> str | None:
    value = data.get(name)
    if not _usable(value, "text_or_null"):
        raise ValueError(f"{tool}: invalid response field {name} (expected text or null)")
    return value
