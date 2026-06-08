from __future__ import annotations

import time
import uuid
from typing import Any

from agentlens.core.events import EventKind, EventStatus, LensEvent
from agentlens.profiler.enricher import TokenEnricher
from agentlens.store.base import AbstractStore

_DEFAULT_INPUT_COST_PER_M = 2.50
_DEFAULT_OUTPUT_COST_PER_M = 10.0


class LensOpenAIClient:
    """
    OpenAI client wrapper that records every chat completion call as a LensEvent.

    Usage:
        import openai
        raw = openai.OpenAI()
        client = LensOpenAIClient(store=store, session_id="my-session", model="gpt-4o")

        async def _real(messages, max_tokens, **kw):
            return raw.chat.completions.create(
                model=client._model, messages=messages, max_tokens=max_tokens, **kw
            )
        client._call_upstream = _real
        response = await client.chat_completions_create(messages=[...], max_tokens=100)
    """

    def __init__(
        self,
        store: AbstractStore,
        session_id: str | None = None,
        enricher: TokenEnricher | None = None,
        model: str = "gpt-4o",
        trace_id: str | None = None,
        input_cost_per_m: float = _DEFAULT_INPUT_COST_PER_M,
        output_cost_per_m: float = _DEFAULT_OUTPUT_COST_PER_M,
    ) -> None:
        self._store = store
        self.session_id = session_id or str(uuid.uuid4())
        self._enricher = enricher or TokenEnricher()
        self._model = model
        self._trace_id = trace_id or str(uuid.uuid4())
        self._input_cost_per_m = input_cost_per_m
        self._output_cost_per_m = output_cost_per_m

    async def chat_completions_create(
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
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            return response
        except Exception as exc:
            status = EventStatus.FAILURE
            error = str(exc)
            raise
        finally:
            latency_ms = (time.monotonic() - start) * 1000
            cost = (
                (input_tokens / 1_000_000) * self._input_cost_per_m
                + (output_tokens / 1_000_000) * self._output_cost_per_m
            )
            event = LensEvent(
                event_id=str(uuid.uuid4()),
                session_id=self.session_id,
                trace_id=self._trace_id,
                span_id=str(uuid.uuid4()),
                parent_span_id=None,
                kind=EventKind.LLM_CALL,
                source="openai",
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
