from __future__ import annotations

import time
import uuid
from typing import Any

from agentlens.core.events import EventKind, EventStatus, LensEvent
from agentlens.profiler.enricher import TokenEnricher
from agentlens.store.base import AbstractStore


class MCPInterceptor:
    def __init__(
        self,
        session_id: str,
        store: AbstractStore,
        enricher: TokenEnricher,
        trace_id: str | None = None,
    ) -> None:
        self._session_id = session_id
        self._store = store
        self._enricher = enricher
        self._trace_id = trace_id or str(uuid.uuid4())

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        source: str,
        task_type: str | None = None,
    ) -> Any:
        span_id = str(uuid.uuid4())
        start = time.monotonic()
        status = EventStatus.SUCCESS
        error: str | None = None
        output_tokens = 0

        input_tokens = self._enricher.count_tokens(str(arguments))

        try:
            result = await self._call_tool_upstream(name=name, arguments=arguments)
            output_tokens = self._enricher.count_tokens(str(result))
            return result
        except Exception as exc:
            status = EventStatus.FAILURE
            error = str(exc)
            raise
        finally:
            latency_ms = (time.monotonic() - start) * 1000
            event = LensEvent(
                event_id=str(uuid.uuid4()),
                session_id=self._session_id,
                trace_id=self._trace_id,
                span_id=span_id,
                parent_span_id=None,
                kind=EventKind.TOOL_CALL,
                source=source,
                name=name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                schema_tokens=0,
                latency_ms=latency_ms,
                status=status,
                error=error,
                task_type=task_type,
                metadata={"arguments": arguments},
            )
            await self._store.save_event(event)

    async def _call_tool_upstream(self, name: str, arguments: dict[str, Any]) -> Any:
        raise NotImplementedError
