# tests/integration/test_postgres_store.py
"""
Postgres store tests. Skipped unless AGENTLENS_TEST_PG_DSN is set.
Example: AGENTLENS_TEST_PG_DSN=postgresql://user:pass@localhost/agentlens_test pytest
"""
import os
import pytest
from datetime import datetime, timezone
from agentlens.core.events import EventKind, EventStatus, LensEvent

PG_DSN = os.environ.get("AGENTLENS_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not PG_DSN, reason="AGENTLENS_TEST_PG_DSN not set")


@pytest.fixture
async def pg_store():
    from agentlens.store.postgres import PostgresStore
    store = PostgresStore(PG_DSN)  # type: ignore[arg-type]
    await store.init()
    yield store
    await store._pool.execute(  # type: ignore[union-attr]
        "DELETE FROM agentlens_events WHERE session_id LIKE 'test-%'"
    )
    await store.close()


def _make_event(event_id: str = "e1", session_id: str = "test-s1") -> LensEvent:
    return LensEvent(
        event_id=event_id, session_id=session_id, trace_id="t1",
        span_id=event_id, parent_span_id=None,
        kind=EventKind.TOOL_CALL, source="srv", name="read_file",
        input_tokens=100, output_tokens=50, schema_tokens=200,
        latency_ms=42.0, status=EventStatus.SUCCESS,
        error=None, task_type="code-review", metadata={"x": 1},
        timestamp=datetime.now(timezone.utc),
    )


async def test_pg_save_and_load_event(pg_store):
    await pg_store.save_event(_make_event())
    loaded = await pg_store.get_events_for_session("test-s1")
    assert len(loaded) == 1
    assert loaded[0].schema_tokens == 200
    assert loaded[0].metadata == {"x": 1}


async def test_pg_get_sessions_by_task(pg_store):
    await pg_store.save_event(_make_event("e1", "test-sa"))
    await pg_store.save_event(_make_event("e2", "test-sb"))
    sessions = await pg_store.get_sessions_by_task("code-review")
    assert "test-sa" in sessions
    assert "test-sb" in sessions


async def test_pg_get_recent_stats(pg_store):
    await pg_store.save_event(_make_event())
    stats = await pg_store.get_recent_stats(days=7)
    assert stats["total_sessions"] >= 1
    assert stats["total_schema_tokens"] >= 200
