"""
Snapshot example: simulate 6 profiled sessions then build a snapshot.

Run: python examples/mcp_snapshot.py
"""
import asyncio
from datetime import datetime, timezone
from agentlens import AgentLens
from agentlens.core.events import EventKind, EventStatus, LensEvent
from agentlens.snapshot.builder import SnapshotBuilder


async def main() -> None:
    lens = AgentLens(store="sqlite:///agentlens_snapshot.db")
    await lens.init()

    for i in range(6):
        async with lens.session(agent_id="review-bot", task_type="code-review") as sess:
            for tool_name in ["read_file", "list_dir"]:
                event = LensEvent(
                    event_id=f"e-{i}-{tool_name}",
                    session_id=sess.session_id,
                    trace_id="t",
                    span_id=f"sp-{i}-{tool_name}",
                    parent_span_id=None,
                    kind=EventKind.TOOL_CALL,
                    source="filesystem-mcp",
                    name=tool_name,
                    input_tokens=50,
                    output_tokens=200,
                    schema_tokens=800,
                    latency_ms=45.0,
                    status=EventStatus.SUCCESS,
                    error=None,
                    task_type="code-review",
                    metadata={},
                    timestamp=datetime.now(timezone.utc),
                )
                await lens._store.save_event(event)

    import aiosqlite
    async with aiosqlite.connect("agentlens_snapshot.db") as conn:
        async with conn.execute(
            "SELECT DISTINCT session_id FROM events WHERE task_type = 'code-review'"
        ) as cursor:
            session_ids = [row[0] for row in await cursor.fetchall()]

    sessions = [await lens._store.get_events_for_session(sid) for sid in session_ids]
    builder = SnapshotBuilder(min_sessions=5)
    snapshot = builder.build(task_type="code-review", sessions=sessions)

    if snapshot:
        print(f"Snapshot built for 'code-review':")
        print(f"  Tools: {[t.name for t in snapshot.tools]}")
        print(f"  Confidence: {snapshot.confidence:.2f}")
        print(f"  Sample size: {snapshot.sample_size} sessions")
        print(f"\nWith this snapshot, agents only load {len(snapshot.tools)} tools")
        print("instead of the full MCP server toolset.")

    await lens.close()


if __name__ == "__main__":
    asyncio.run(main())
