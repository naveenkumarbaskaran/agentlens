from __future__ import annotations

from collections import Counter, defaultdict

from agentlens.core.events import EventKind, LensEvent
from agentlens.snapshot.models import SnapshotTool, ToolSnapshot


class SnapshotBuilder:
    def __init__(self, min_sessions: int = 5, min_probability: float = 0.4) -> None:
        self._min_sessions = min_sessions
        self._min_probability = min_probability

    def build(
        self,
        task_type: str,
        sessions: list[list[LensEvent]],
    ) -> ToolSnapshot | None:
        n = len(sessions)
        if n < self._min_sessions:
            return None

        tool_counts: Counter[str] = Counter()
        tool_positions: defaultdict[str, list[int]] = defaultdict(list)
        tool_servers: dict[str, str] = {}

        for sess_events in sessions:
            tool_calls = [e for e in sess_events if e.kind == EventKind.TOOL_CALL]
            seen_in_session: set[str] = set()
            for pos, evt in enumerate(tool_calls):
                if evt.name not in seen_in_session:
                    tool_counts[evt.name] += 1
                    seen_in_session.add(evt.name)
                tool_positions[evt.name].append(pos)
                tool_servers[evt.name] = evt.source

        snapshot = ToolSnapshot.new(task_type=task_type)
        snapshot.sample_size = n

        tools: list[SnapshotTool] = []
        for name, count in tool_counts.items():
            prob = count / n
            if prob < self._min_probability:
                continue
            avg_pos = sum(tool_positions[name]) / len(tool_positions[name])
            tools.append(
                SnapshotTool(
                    name=name,
                    server=tool_servers[name],
                    call_probability=prob,
                    avg_position=avg_pos,
                )
            )

        tools.sort(key=lambda t: t.avg_position)
        snapshot.tools = tools
        snapshot.confidence = min(1.0, n / (self._min_sessions * 4))
        return snapshot
