from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from agentlens.core.events import LensEvent


@dataclass
class CallGraph:
    events: list[LensEvent]
    _by_span: dict[str, LensEvent] = field(default_factory=dict, repr=False)
    _children: dict[str, list[LensEvent]] = field(
        default_factory=lambda: defaultdict(list), repr=False
    )

    @classmethod
    def from_events(cls, events: list[LensEvent]) -> "CallGraph":
        graph = cls(events=events)
        for evt in events:
            graph._by_span[evt.span_id] = evt
            if evt.parent_span_id:
                graph._children[evt.parent_span_id].append(evt)
        return graph

    @property
    def roots(self) -> list[LensEvent]:
        return [e for e in self.events if e.parent_span_id is None]

    def children_of(self, span_id: str) -> list[LensEvent]:
        return self._children.get(span_id, [])

    @property
    def total_schema_tokens(self) -> int:
        return sum(e.schema_tokens for e in self.events)
