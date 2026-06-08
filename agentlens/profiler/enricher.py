from __future__ import annotations

import json
from typing import Any

import tiktoken

# Cost per million tokens by model family
_COST_TABLE: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-8": (15.0, 75.0),
    "claude-haiku-4-5-20251001": (0.8, 4.0),
    "default": (3.0, 15.0),
}


class TokenEnricher:
    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        self._model = model
        # tiktoken uses cl100k_base for Claude-family counting approximation
        self._enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self._enc.encode(text))

    def count_schema_tokens(self, schema: dict[str, Any]) -> int:
        return self.count_tokens(json.dumps(schema))

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_rate, output_rate = _COST_TABLE.get(
            self._model, _COST_TABLE["default"]
        )
        return (input_tokens / 1_000_000) * input_rate + (
            output_tokens / 1_000_000
        ) * output_rate
