from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg

from agentlens.core.events import EventKind, EventStatus, LensEvent

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS agentlens_events (
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
    latency_ms     DOUBLE PRECISION NOT NULL,
    status         TEXT NOT NULL,
    error          TEXT,
    task_type      TEXT,
    metadata       JSONB NOT NULL DEFAULT '{}',
    timestamp      TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_al_events_session ON agentlens_events(session_id);
CREATE INDEX IF NOT EXISTS idx_al_events_task    ON agentlens_events(task_type);
CREATE INDEX IF NOT EXISTS idx_al_events_ts      ON agentlens_events(timestamp);
"""


class PostgresStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def init(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn)
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_TABLE)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def save_event(self, event: LensEvent) -> None:
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO agentlens_events VALUES
                   ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
                   ON CONFLICT (event_id) DO UPDATE SET
                   input_tokens=EXCLUDED.input_tokens,
                   output_tokens=EXCLUDED.output_tokens,
                   schema_tokens=EXCLUDED.schema_tokens,
                   status=EXCLUDED.status,
                   error=EXCLUDED.error""",
                event.event_id, event.session_id, event.trace_id,
                event.span_id, event.parent_span_id,
                event.kind.value, event.source, event.name,
                event.input_tokens, event.output_tokens, event.schema_tokens,
                event.latency_ms, event.status.value, event.error,
                event.task_type, json.dumps(event.metadata),
                event.timestamp,
            )

    async def get_events_for_session(self, session_id: str) -> list[LensEvent]:
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM agentlens_events WHERE session_id=$1 ORDER BY timestamp",
                session_id,
            )
        return [_row_to_event(dict(row)) for row in rows]

    async def get_sessions_by_task(self, task_type: str) -> list[str]:
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT session_id FROM agentlens_events WHERE task_type=$1 ORDER BY session_id",
                task_type,
            )
        return [row["session_id"] for row in rows]

    async def get_recent_stats(self, days: int = 7) -> dict[str, Any]:
        assert self._pool is not None
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT
                     COUNT(DISTINCT session_id),
                     COALESCE(SUM(input_tokens), 0),
                     COALESCE(SUM(output_tokens), 0),
                     COALESCE(SUM(schema_tokens), 0)
                   FROM agentlens_events WHERE timestamp >= $1""",
                cutoff,
            )
        total_sessions = row[0]
        total_in = row[1]
        total_out = row[2]
        total_schema = row[3]
        total_with_schema = total_in + total_schema
        waste_pct = (total_schema / total_with_schema * 100) if total_with_schema > 0 else 0.0
        return {
            "total_sessions": total_sessions,
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "total_schema_tokens": total_schema,
            "schema_waste_pct": waste_pct,
        }


def _row_to_event(row: dict[str, Any]) -> LensEvent:
    ts = row["timestamp"]
    if isinstance(ts, datetime):
        ts = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
    else:
        ts = datetime.fromisoformat(str(ts)).replace(tzinfo=timezone.utc)
    metadata = row["metadata"]
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    return LensEvent(
        event_id=row["event_id"], session_id=row["session_id"],
        trace_id=row["trace_id"], span_id=row["span_id"],
        parent_span_id=row["parent_span_id"],
        kind=EventKind(row["kind"]), source=row["source"], name=row["name"],
        input_tokens=row["input_tokens"], output_tokens=row["output_tokens"],
        schema_tokens=row["schema_tokens"], latency_ms=float(row["latency_ms"]),
        status=EventStatus(row["status"]), error=row["error"],
        task_type=row["task_type"], metadata=metadata, timestamp=ts,
    )
