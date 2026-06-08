from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentlens.snapshot.models import ToolSnapshot
    from agentlens.store.sqlite import SQLiteStore


class SnapshotStore:
    def __init__(self, store: "SQLiteStore") -> None:
        self._store = store

    async def save(self, snapshot: "ToolSnapshot") -> None:
        await self._store.save_snapshot(snapshot)

    async def load(self, task_type: str) -> "ToolSnapshot | None":
        return await self._store.load_snapshot(task_type)
