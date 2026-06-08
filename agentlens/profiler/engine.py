from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from agentlens.core.events import LensEvent
from agentlens.store.base import AbstractStore

EventHandler = Callable[[LensEvent], Awaitable[None]]


class ProfilerEngine:
    def __init__(self, store: AbstractStore) -> None:
        self._store = store
        self._queue: asyncio.Queue[LensEvent] = asyncio.Queue()
        self._handlers: list[EventHandler] = []
        self._task: asyncio.Task[None] | None = None

    def add_handler(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    async def start(self) -> None:
        self._task = asyncio.create_task(self._drain())

    async def stop(self) -> None:
        await self._queue.join()
        if self._task:
            self._task.cancel()

    async def emit(self, event: LensEvent) -> None:
        await self._queue.put(event)

    async def _drain(self) -> None:
        while True:
            event = await self._queue.get()
            try:
                await self._store.save_event(event)
                for handler in self._handlers:
                    await handler(event)
            finally:
                self._queue.task_done()
