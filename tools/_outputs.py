from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


def emit(tool: Tool, payload: dict[str, Any]) -> Generator[ToolInvokeMessage]:
    """Emit a result as one JSON message plus one variable message per field.

    A Dify workflow node can address a tool's individual outputs by name
    (``{{#node.field#}}``) only when the tool emits variable messages; a JSON
    message alone surfaces under the single ``json`` output and leaves named
    selectors unresolved at runtime. Emitting both keeps the ``json`` blob and
    makes every field resolvable as ``[node, key]``.
    """
    yield tool.create_json_message(payload)
    for key, value in payload.items():
        yield tool.create_variable_message(key, value)
