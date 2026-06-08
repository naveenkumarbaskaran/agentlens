# tests/unit/test_snapshot_builder.py
from datetime import datetime, timezone
from agentlens.core.events import EventKind, EventStatus, LensEvent
from agentlens.snapshot.builder import SnapshotBuilder


def _tool_call(name: str, schema_tokens: int = 100) -> LensEvent:
    return LensEvent(
        event_id=f"e-{name}", session_id="s1", trace_id="t", span_id=f"sp-{name}",
        parent_span_id=None, kind=EventKind.TOOL_CALL, source="mcp-srv",
        name=name, input_tokens=50, output_tokens=20, schema_tokens=schema_tokens,
        latency_ms=30.0, status=EventStatus.SUCCESS, error=None,
        task_type="code-review", metadata={}, timestamp=datetime.now(timezone.utc),
    )


def test_build_snapshot_from_events():
    all_events: list[list[LensEvent]] = []
    for _ in range(5):
        all_events.append([_tool_call("read_file"), _tool_call("list_dir")])

    builder = SnapshotBuilder(min_sessions=3)
    snapshot = builder.build(task_type="code-review", sessions=all_events)

    assert snapshot is not None
    assert snapshot.task_type == "code-review"
    assert len(snapshot.tools) == 2
    tool_names = {t.name for t in snapshot.tools}
    assert "read_file" in tool_names
    assert "list_dir" in tool_names


def test_build_snapshot_insufficient_sessions():
    all_events = [[_tool_call("read_file")]]
    builder = SnapshotBuilder(min_sessions=3)
    snapshot = builder.build(task_type="code-review", sessions=all_events)
    assert snapshot is None


def test_snapshot_call_probability():
    sessions = [
        [_tool_call("read_file"), _tool_call("list_dir")],
        [_tool_call("read_file"), _tool_call("list_dir")],
        [_tool_call("read_file")],
        [_tool_call("read_file")],
    ]
    builder = SnapshotBuilder(min_sessions=3)
    snapshot = builder.build(task_type="code-review", sessions=sessions)
    assert snapshot is not None
    by_name = {t.name: t for t in snapshot.tools}
    assert by_name["read_file"].call_probability == 1.0
    assert by_name["list_dir"].call_probability == 0.5
