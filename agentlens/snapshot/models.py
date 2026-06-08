from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class SnapshotTool:
    name: str
    server: str
    call_probability: float
    avg_position: float
    compressed_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolSnapshot:
    snapshot_id: str
    task_type: str
    version: int
    tools: list[SnapshotTool]
    avg_token_savings: float
    confidence: float
    sample_size: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = field(default_factory=list)

    @classmethod
    def new(cls, task_type: str, version: int = 1) -> "ToolSnapshot":
        return cls(
            snapshot_id=str(uuid.uuid4()),
            task_type=task_type,
            version=version,
            tools=[],
            avg_token_savings=0.0,
            confidence=0.0,
            sample_size=0,
        )
