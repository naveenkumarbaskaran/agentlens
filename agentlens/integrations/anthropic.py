from __future__ import annotations

import time
import uuid
from typing import Any

from agentlens.core.events import EventKind, EventStatus, LensEvent
from agentlens.profiler.enricher import TokenEnricher
from agentlens.store.base import AbstractStore


class LensAnthropicClient:
    def __init__(
        self,
        session_id: str,
        store: AbstractStore,
        enricher: TokenEnricher,
        model: str = "claude-sonnet-4-6",
        trace_id: str | None = None,
    ) -> None:
        self._session_id = session_id
        self._store = store
        self._enricher = enricher
        self._model = model
        self._trace_id = trace_id or str(uuid.uuid4())

    async def messages_create(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int,
        **kwargs: Any,
    ) -> Any:
        start = time.monotonic()
        status = EventStatus.SUCCESS
        error: str | None = None
        input_tokens = output_tokens = 0

        try:
            response = await self._call_upstream(
                messages=messages, max_tokens=max_tokens, **kwargs
            )
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            return response
        except Exception as exc:
            status = EventStatus.FAILURE
            error = str(exc)
            raise
        finally:
            latency_ms = (time.monotonic() - start) * 1000
            cost = self._enricher.estimate_cost(input_tokens, output_tokens)
            event = LensEvent(
                event_id=str(uuid.uuid4()),
                session_id=self._session_id,
                trace_id=self._trace_id,
                span_id=str(uuid.uuid4()),
                parent_span_id=None,
                kind=EventKind.LLM_CALL,
                source="anthropic",
                name=self._model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                schema_tokens=0,
                latency_ms=latency_ms,
                status=status,
                error=error,
                task_type=None,
                metadata={"cost_usd": cost},
            )
            await self._store.save_event(event)

    async def _call_upstream(self, **kwargs: Any) -> Any:
        raise NotImplementedError
