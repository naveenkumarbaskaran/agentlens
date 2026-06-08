from __future__ import annotations

import json
from datetime import datetime, timezone

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


class SQLiteStore:
    def __init__(self, path: str) -> None:
        self._path = path.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._db = await aiosqlite.connect(self._path)
        await self._db.executescript(_CREATE_EVENTS)
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
