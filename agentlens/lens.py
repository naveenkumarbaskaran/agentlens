from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from agentlens.core.session import LensSession, SessionManager
from agentlens.integrations.anthropic import LensAnthropicClient
from agentlens.integrations.mcp.interceptor import MCPInterceptor
from agentlens.profiler.classifier import TaskClassifier
from agentlens.profiler.enricher import TokenEnricher
from agentlens.store.sqlite import SQLiteStore


class AgentLens:
    def __init__(
        self,
        store: str = "sqlite:///agentlens.db",
        model: str = "claude-sonnet-4-6",
    ) -> None:
        self._store_url = store
        self._model = model
        self._store = SQLiteStore(store)
        self._enricher = TokenEnricher(model=model)
        self._manager = SessionManager()

    async def init(self) -> None:
        await self._store.init()

    async def close(self) -> None:
        await self._store.close()

    @asynccontextmanager
    async def session(
        self,
        agent_id: str,
        framework: str = "raw",
        task_type: str | None = None,
    ) -> AsyncIterator[LensSession]:
        async with self._manager.session(
            agent_id=agent_id, framework=framework
        ) as sess:
            yield sess

    def wrap_mcp(self, session: LensSession, source: str) -> MCPInterceptor:
        return MCPInterceptor(
            session_id=session.session_id,
            store=self._store,
            enricher=self._enricher,
        )

    def wrap_anthropic(self, session: LensSession) -> LensAnthropicClient:
        return LensAnthropicClient(
            session_id=session.session_id,
            store=self._store,
            enricher=self._enricher,
            model=self._model,
        )

    async def classify_task(
        self,
        message: str,
        known_task_types: list[str],
        classifier_model: str = "claude-haiku-4-5-20251001",
    ) -> str | None:
        classifier = TaskClassifier(
            known_task_types=known_task_types,
            model=classifier_model,
        )
        return await classifier.classify(message)
