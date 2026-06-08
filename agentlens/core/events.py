from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventKind(str, Enum):
    TOOL_CALL = "tool_call"
    MCP_SCHEMA_LOAD = "mcp_schema_load"
    AGENT_INVOKE = "agent_invoke"
    LLM_CALL = "llm_call"


class EventStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class LensEvent:
    event_id: str
    session_id: str
    trace_id: str
    span_id: str
    parent_span_id: str | None

    kind: EventKind
    source: str
    name: str

    input_tokens: int
    output_tokens: int
    schema_tokens: int
    latency_ms: float

    status: EventStatus
    error: str | None

    task_type: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
