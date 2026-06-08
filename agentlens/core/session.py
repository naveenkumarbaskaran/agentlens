from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator

from agentlens.core.context import current_session

# Cost per million tokens (claude-sonnet-4-6 defaults)
_INPUT_COST_PER_M = 3.0
_OUTPUT_COST_PER_M = 15.0


@dataclass
class LensSession:
    session_id: str
    agent_id: str
    framework: str
    snapshot_id: str | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_schema_tokens: int = 0
    total_cost_usd: float = 0.0
    duration_ms: float = 0.0

    def add_tokens(
        self,
        input_tokens: int,
        output_tokens: int,
        schema_tokens: int,
        input_cost_per_m: float = _INPUT_COST_PER_M,
        output_cost_per_m: float = _OUTPUT_COST_PER_M,
    ) -> None:
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_schema_tokens += schema_tokens
        self.total_cost_usd += (input_tokens / 1_000_000) * input_cost_per_m
        self.total_cost_usd += (output_tokens / 1_000_000) * output_cost_per_m


class SessionManager:
    @asynccontextmanager
    async def session(
        self,
        agent_id: str,
        framework: str = "raw",
        snapshot_id: str | None = None,
    ) -> AsyncIterator[LensSession]:
        sess = LensSession(
            session_id=str(uuid.uuid4()),
            agent_id=agent_id,
            framework=framework,
            snapshot_id=snapshot_id,
        )
        token = current_session.set(sess)
        try:
            yield sess
        finally:
            current_session.reset(token)
