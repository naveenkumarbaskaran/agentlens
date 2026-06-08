# tests/unit/test_call_graph.py
from datetime import datetime, timezone
from agentlens.core.events import EventKind, EventStatus, LensEvent
from agentlens.profiler.call_graph import CallGraph


def _evt(event_id: str, span_id: str, parent_span_id: str | None, kind: EventKind) -> LensEvent:
    return LensEvent(
        event_id=event_id, session_id="s", trace_id="t",
        span_id=span_id, parent_span_id=parent_span_id,
        kind=kind, source="srv", name="tool_a",
        input_tokens=10, output_tokens=5, schema_tokens=50,
        latency_ms=10.0, status=EventStatus.SUCCESS,
        error=None, task_type="code-review", metadata={},
        timestamp=datetime.now(timezone.utc),
    )


def test_call_graph_root_events():
    events = [
        _evt("e1", "sp1", None, EventKind.MCP_SCHEMA_LOAD),
        _evt("e2", "sp2", "sp1", EventKind.TOOL_CALL),
        _evt("e3", "sp3", None, EventKind.LLM_CALL),
    ]
    graph = CallGraph.from_events(events)
    assert len(graph.roots) == 2  # e1 and e3 have no parent


def test_call_graph_children():
    events = [
        _evt("e1", "sp1", None, EventKind.LLM_CALL),
        _evt("e2", "sp2", "sp1", EventKind.TOOL_CALL),
        _evt("e3", "sp3", "sp1", EventKind.TOOL_CALL),
    ]
    graph = CallGraph.from_events(events)
    children = graph.children_of("sp1")
    assert len(children) == 2


def test_call_graph_total_schema_tokens():
    events = [
        _evt("e1", "sp1", None, EventKind.MCP_SCHEMA_LOAD),
        _evt("e2", "sp2", None, EventKind.MCP_SCHEMA_LOAD),
    ]
    graph = CallGraph.from_events(events)
    assert graph.total_schema_tokens == 100  # 50 each
