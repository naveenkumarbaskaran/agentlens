from __future__ import annotations

from agentlens.snapshot.models import ToolSnapshot


class ToolOptimizer:
    def select_tools(
        self,
        available_tools: list[str],
        snapshot: ToolSnapshot,
    ) -> list[str]:
        snapshot_names = [t.name for t in snapshot.tools]
        available_set = set(available_tools)
        return [name for name in snapshot_names if name in available_set]
