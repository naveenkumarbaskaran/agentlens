# tests/integration/test_sqlite_store.py
from datetime import datetime, timezone
import pytest
from agentlens.core.events import EventKind, EventStatus, LensEvent
from agentlens.store.sqlite import SQLiteStore


def _make_event(event_id: str = "e1", session_id: str = "s1") -> LensEvent:
    return LensEvent(
        event_id=event_id, session_id=session_id, trace_id="t1",
        span_id=event_id, parent_span_id=None,
        kind=EventKind.TOOL_CALL, source="srv", name="read_file",
        input_tokens=100, output_tokens=50, schema_tokens=200,
        latency_ms=42.0, status=EventStatus.SUCCESS,
        error=None, task_type="code-review", metadata={"x": 1},
        timestamp=datetime.now(timezone.utc),
    )


async def test_save_and_load_event(store):
    event = _make_event()
    await store.save_event(event)
    loaded = await store.get_events_for_session("s1")
    assert len(loaded) == 1
    assert loaded[0].event_id == "e1"
    assert loaded[0].schema_tokens == 200
    assert loaded[0].metadata == {"x": 1}


async def test_multiple_events_same_session(store):
    await store.save_event(_make_event("e1", "sess-a"))
    await store.save_event(_make_event("e2", "sess-a"))
    await store.save_event(_make_event("e3", "sess-b"))
    a_events = await store.get_events_for_session("sess-a")
    b_events = await store.get_events_for_session("sess-b")
    assert len(a_events) == 2
    assert len(b_events) == 1


async def test_get_events_empty_session(store):
    result = await store.get_events_for_session("nonexistent")
    assert result == []


async def test_get_sessions_by_task(store):
    from datetime import datetime, timezone
    from agentlens.core.events import EventKind, EventStatus, LensEvent

    def _evt(event_id: str, session_id: str, task_type: str) -> LensEvent:
        return LensEvent(
            event_id=event_id, session_id=session_id, trace_id="t",
            span_id=event_id, parent_span_id=None,
            kind=EventKind.TOOL_CALL, source="srv", name="read_file",
            input_tokens=10, output_tokens=5, schema_tokens=100,
            latency_ms=20.0, status=EventStatus.SUCCESS,
            error=None, task_type=task_type, metadata={},
            timestamp=datetime.now(timezone.utc),
        )

    await store.save_event(_evt("e1", "sess-a", "code-review"))
    await store.save_event(_evt("e2", "sess-a", "code-review"))
    await store.save_event(_evt("e3", "sess-b", "code-review"))
    await store.save_event(_evt("e4", "sess-c", "db-query"))

    sessions = await store.get_sessions_by_task("code-review")
    assert set(sessions) == {"sess-a", "sess-b"}

    sessions2 = await store.get_sessions_by_task("db-query")
    assert sessions2 == ["sess-c"]

    sessions3 = await store.get_sessions_by_task("unknown")
    assert sessions3 == []


async def test_get_recent_stats(store):
    import pytest
    from datetime import datetime, timezone
    from agentlens.core.events import EventKind, EventStatus, LensEvent

    event = LensEvent(
        event_id="e1", session_id="sess-x", trace_id="t",
        span_id="sp1", parent_span_id=None,
        kind=EventKind.TOOL_CALL, source="srv", name="read_file",
        input_tokens=500, output_tokens=200, schema_tokens=1000,
        latency_ms=30.0, status=EventStatus.SUCCESS,
        error=None, task_type="code-review", metadata={},
        timestamp=datetime.now(timezone.utc),
    )
    await store.save_event(event)

    stats = await store.get_recent_stats(days=7)
    assert stats["total_sessions"] == 1
    assert stats["total_input_tokens"] == 500
    assert stats["total_output_tokens"] == 200
    assert stats["total_schema_tokens"] == 1000
    assert stats["schema_waste_pct"] == pytest.approx(66.67, rel=0.01)
