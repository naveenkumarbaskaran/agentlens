from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from agentlens.core.events import EventKind, EventStatus, LensEvent

_CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
    event_id       TEXT PRIMARY KEY,
    session_id     TEXT NOT NULL,
    trace_id       TEXT NOT NULL,
    span_id        TEXT NOT NULL,
    parent_span_id TEXT,
    kind           TEXT NOT NULL,
    source         TEXT NOT NULL,
    name           TEXT NOT NULL,
    input_tokens   INTEGER NOT NULL,
    output_tokens  INTEGER NOT NULL,
    schema_tokens  INTEGER NOT NULL,
    latency_ms     REAL NOT NULL,
    status         TEXT NOT NULL,
    error          TEXT,
    task_type      TEXT,
    metadata       TEXT NOT NULL,
    timestamp      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
"""

_CREATE_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS snapshots (
    task_type         TEXT PRIMARY KEY,
    snapshot_id       TEXT NOT NULL,
    version           INTEGER NOT NULL,
    confidence        REAL NOT NULL,
    sample_size       INTEGER NOT NULL,
    avg_token_savings REAL NOT NULL,
    tools_json        TEXT NOT NULL,
    tags_json         TEXT NOT NULL,
    created_at        TEXT NOT NULL
);
"""


class SQLiteStore:
    def __init__(self, path: str) -> None:
        self._path = path.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._db = await aiosqlite.connect(self._path)
        await self._db.executescript(_CREATE_EVENTS)
        await self._db.commit()
        await self._db.executescript(_CREATE_SNAPSHOTS)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def save_event(self, event: LensEvent) -> None:
        assert self._db is not None
        await self._db.execute(
            "INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                event.event_id, event.session_id, event.trace_id,
                event.span_id, event.parent_span_id,
                event.kind.value, event.source, event.name,
                event.input_tokens, event.output_tokens, event.schema_tokens,
                event.latency_ms, event.status.value, event.error,
                event.task_type, json.dumps(event.metadata),
                event.timestamp.isoformat(),
            ),
        )
        await self._db.commit()

    async def get_events_for_session(self, session_id: str) -> list[LensEvent]:
        assert self._db is not None
        async with self._db.execute(
            "SELECT * FROM events WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [_row_to_event(row) for row in rows]

    async def get_sessions_by_task(self, task_type: str) -> list[str]:
        assert self._db is not None
        async with self._db.execute(
            "SELECT DISTINCT session_id FROM events WHERE task_type = ? ORDER BY session_id",
            (task_type,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def get_recent_stats(self, days: int = 7) -> dict[str, Any]:
        assert self._db is not None
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        async with self._db.execute(
            """SELECT
                COUNT(DISTINCT session_id),
                COALESCE(SUM(input_tokens), 0),
                COALESCE(SUM(output_tokens), 0),
                COALESCE(SUM(schema_tokens), 0)
               FROM events WHERE timestamp >= ?""",
            (cutoff,),
        ) as cursor:
            row = await cursor.fetchone()
        total_sessions, total_in, total_out, total_schema = row  # type: ignore[misc]
        total_with_schema = total_in + total_schema
        waste_pct = (total_schema / total_with_schema * 100) if total_with_schema > 0 else 0.0
        return {
            "total_sessions": total_sessions,
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "total_schema_tokens": total_schema,
            "schema_waste_pct": waste_pct,
        }

    async def save_snapshot(self, snapshot: "ToolSnapshot") -> None:
        import json as _json
        assert self._db is not None
        tools_data = [
            {
                "name": t.name,
                "server": t.server,
                "call_probability": t.call_probability,
                "avg_position": t.avg_position,
                "compressed_schema": t.compressed_schema,
            }
            for t in snapshot.tools
        ]
        await self._db.execute(
            "INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?,?,?)",
            (
                snapshot.task_type,
                snapshot.snapshot_id,
                snapshot.version,
                snapshot.confidence,
                snapshot.sample_size,
                snapshot.avg_token_savings,
                _json.dumps(tools_data),
                _json.dumps(snapshot.tags),
                snapshot.created_at.isoformat(),
            ),
        )
        await self._db.commit()

    async def load_snapshot(self, task_type: str) -> "ToolSnapshot | None":
        import json as _json
        from datetime import datetime, timezone
        from agentlens.snapshot.models import SnapshotTool, ToolSnapshot
        assert self._db is not None
        async with self._db.execute(
            "SELECT * FROM snapshots WHERE task_type = ?", (task_type,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        (
            task_type_, snapshot_id, version, confidence, sample_size,
            avg_token_savings, tools_json, tags_json, created_at,
        ) = row
        tools = [
            SnapshotTool(
                name=t["name"],
                server=t["server"],
                call_probability=t["call_probability"],
                avg_position=t["avg_position"],
                compressed_schema=t.get("compressed_schema", {}),
            )
            for t in _json.loads(tools_json)
        ]
        return ToolSnapshot(
            snapshot_id=snapshot_id,
            task_type=task_type_,
            version=version,
            tools=tools,
            avg_token_savings=avg_token_savings,
            confidence=confidence,
            sample_size=sample_size,
            created_at=datetime.fromisoformat(created_at).replace(tzinfo=timezone.utc),
            tags=_json.loads(tags_json),
        )


def _row_to_event(row: tuple) -> LensEvent:  # type: ignore[type-arg]
    (
        event_id, session_id, trace_id, span_id, parent_span_id,
        kind, source, name,
        input_tokens, output_tokens, schema_tokens, latency_ms,
        status, error, task_type, metadata, timestamp,
    ) = row
    return LensEvent(
        event_id=event_id, session_id=session_id, trace_id=trace_id,
        span_id=span_id, parent_span_id=parent_span_id,
        kind=EventKind(kind), source=source, name=name,
        input_tokens=input_tokens, output_tokens=output_tokens,
        schema_tokens=schema_tokens, latency_ms=latency_ms,
        status=EventStatus(status), error=error,
        task_type=task_type, metadata=json.loads(metadata),
        timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
    )
