from __future__ import annotations

import time
import uuid
from typing import Any
from uuid import UUID

from agentlens.core.events import EventKind, EventStatus, LensEvent
from agentlens.profiler.enricher import TokenEnricher
from agentlens.store.base import AbstractStore


class LangChainLensCallback:
    """
    LangChain callback handler that records LLM calls and tool calls as LensEvents.

    Usage:
        cb = LangChainLensCallback(store=store, session_id="my-session")
        chain.invoke({"input": "..."}, config={"callbacks": [cb]})
    """

    def __init__(
        self,
        store: AbstractStore,
        session_id: str | None = None,
        model: str = "claude-sonnet-4-6",
        task_type: str | None = None,
    ) -> None:
        self._store = store
        self.session_id = session_id or str(uuid.uuid4())
        self._enricher = TokenEnricher(model=model)
        self._model = model
        self._task_type = task_type
        self._trace_id = str(uuid.uuid4())
        # Track in-flight runs: run_id -> {start_time, name, span_id, ...}
        self._runs: dict[str, dict[str, Any]] = {}

    # ── LLM events ───────────────────────────────────────────────────────────

    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        run_id: str | UUID,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        self._runs[rid] = {
            "start": time.monotonic(),
            "name": serialized.get("name", self._model),
            "span_id": str(uuid.uuid4()),
            "kind": "llm",
        }

    async def on_llm_end(
        self,
        response: Any,
        run_id: str | UUID,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        run = self._runs.pop(rid, {})
        latency_ms = (time.monotonic() - run.get("start", time.monotonic())) * 1000

        input_tokens = output_tokens = 0
        try:
            gen = response.generations[0][0]
            usage = getattr(gen.message, "usage_metadata", None) or {}
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
        except (IndexError, AttributeError):
            pass

        cost = self._enricher.estimate_cost(input_tokens, output_tokens)
        event = LensEvent(
            event_id=str(uuid.uuid4()),
            session_id=self.session_id,
            trace_id=self._trace_id,
            span_id=run.get("span_id", str(uuid.uuid4())),
            parent_span_id=None,
            kind=EventKind.LLM_CALL,
            source="langchain",
            name=run.get("name", self._model),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            schema_tokens=0,
            latency_ms=latency_ms,
            status=EventStatus.SUCCESS,
            error=None,
            task_type=self._task_type,
            metadata={"cost_usd": cost},
        )
        await self._store.save_event(event)

    async def on_llm_error(
        self,
        error: BaseException,
        run_id: str | UUID,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        run = self._runs.pop(rid, {})
        latency_ms = (time.monotonic() - run.get("start", time.monotonic())) * 1000
        event = LensEvent(
            event_id=str(uuid.uuid4()),
            session_id=self.session_id,
            trace_id=self._trace_id,
            span_id=run.get("span_id", str(uuid.uuid4())),
            parent_span_id=None,
            kind=EventKind.LLM_CALL,
            source="langchain",
            name=run.get("name", self._model),
            input_tokens=0,
            output_tokens=0,
            schema_tokens=0,
            latency_ms=latency_ms,
            status=EventStatus.FAILURE,
            error=str(error),
            task_type=self._task_type,
            metadata={},
        )
        await self._store.save_event(event)

    # ── Tool events ──────────────────────────────────────────────────────────

    async def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        run_id: str | UUID,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        self._runs[rid] = {
            "start": time.monotonic(),
            "name": serialized.get("name", "unknown_tool"),
            "span_id": str(uuid.uuid4()),
            "input_tokens": self._enricher.count_tokens(input_str),
            "kind": "tool",
        }

    async def on_tool_end(
        self,
        output: str,
        run_id: str | UUID,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        run = self._runs.pop(rid, {})
        latency_ms = (time.monotonic() - run.get("start", time.monotonic())) * 1000
        output_tokens = self._enricher.count_tokens(str(output))
        event = LensEvent(
            event_id=str(uuid.uuid4()),
            session_id=self.session_id,
            trace_id=self._trace_id,
            span_id=run.get("span_id", str(uuid.uuid4())),
            parent_span_id=None,
            kind=EventKind.TOOL_CALL,
            source="langchain",
            name=run.get("name", "unknown_tool"),
            input_tokens=run.get("input_tokens", 0),
            output_tokens=output_tokens,
            schema_tokens=0,
            latency_ms=latency_ms,
            status=EventStatus.SUCCESS,
            error=None,
            task_type=self._task_type,
            metadata={},
        )
        await self._store.save_event(event)

    async def on_tool_error(
        self,
        error: BaseException,
        run_id: str | UUID,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        run = self._runs.pop(rid, {})
        latency_ms = (time.monotonic() - run.get("start", time.monotonic())) * 1000
        event = LensEvent(
            event_id=str(uuid.uuid4()),
            session_id=self.session_id,
            trace_id=self._trace_id,
            span_id=run.get("span_id", str(uuid.uuid4())),
            parent_span_id=None,
            kind=EventKind.TOOL_CALL,
            source="langchain",
            name=run.get("name", "unknown_tool"),
            input_tokens=run.get("input_tokens", 0),
            output_tokens=0,
            schema_tokens=0,
            latency_ms=latency_ms,
            status=EventStatus.FAILURE,
            error=str(error),
            task_type=self._task_type,
            metadata={},
        )
        await self._store.save_event(event)
