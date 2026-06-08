from __future__ import annotations

from typing import Any


class SchemaCompressor:
    def __init__(self, max_description_chars: int = 200) -> None:
        self._max_desc = max_description_chars

    def compress(self, schema: dict[str, Any]) -> dict[str, Any]:
        result = dict(schema)
        desc = result.get("description", "")
        if len(desc) > self._max_desc:
            result["description"] = desc[: self._max_desc - 3] + "..."
        return result
