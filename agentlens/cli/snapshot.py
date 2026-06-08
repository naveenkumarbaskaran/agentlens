from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Manage tool snapshots")
console = Console()


@app.command("list")
def list_snapshots(
    db: str = typer.Option("agentlens.db", help="Path to AgentLens SQLite database"),
) -> None:
    """List all saved snapshots."""
    asyncio.run(_list_snapshots(db))


@app.command("build")
def build_snapshot(
    task_type: str = typer.Argument(..., help="Task type to build snapshot for"),
    min_sessions: int = typer.Option(5, help="Minimum sessions required"),
    db: str = typer.Option("agentlens.db", help="Path to AgentLens SQLite database"),
) -> None:
    """Build a snapshot from recorded sessions for a task type."""
    asyncio.run(_build_snapshot(task_type, min_sessions, db))


async def _list_snapshots(db: str) -> None:
    import aiosqlite

    try:
        async with aiosqlite.connect(db) as conn:
            async with conn.execute(
                "SELECT snapshot_id, task_type, version, confidence, sample_size, avg_token_savings, created_at "
                "FROM snapshots ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
    except Exception:
        rows = []

    if not rows:
        console.print("[yellow]No snapshots found.[/yellow]")
        return

    table = Table(title="AgentLens Snapshots")
    table.add_column("Task Type", style="green")
    table.add_column("Version", justify="right")
    table.add_column("Confidence", justify="right")
    table.add_column("Sessions", justify="right")
    table.add_column("Avg Token Savings", justify="right", style="cyan")
    table.add_column("Created")

    for row in rows:
        _, task_type, version, confidence, sample_size, savings, created_at = row
        table.add_row(
            task_type, str(version), f"{confidence:.2f}",
            str(sample_size), f"{savings:.1f}%", created_at[:10],
        )
    console.print(table)


async def _build_snapshot(task_type: str, min_sessions: int, db: str) -> None:
    import aiosqlite
    from agentlens.store.sqlite import SQLiteStore
    from agentlens.snapshot.builder import SnapshotBuilder

    store = SQLiteStore(db)
    await store.init()

    async with aiosqlite.connect(db) as conn:
        async with conn.execute(
            "SELECT DISTINCT session_id FROM events WHERE task_type = ?", (task_type,)
        ) as cursor:
            session_ids = [row[0] for row in await cursor.fetchall()]

    sessions = []
    for sid in session_ids:
        events = await store.get_events_for_session(sid)
        sessions.append(events)

    await store.close()

    builder = SnapshotBuilder(min_sessions=min_sessions)
    snapshot = builder.build(task_type=task_type, sessions=sessions)

    if snapshot is None:
        console.print(f"[red]Not enough sessions ({len(sessions)} found, {min_sessions} required)[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Snapshot built: {len(snapshot.tools)} tools, confidence {snapshot.confidence:.2f}[/green]")
    for t in snapshot.tools:
        console.print(f"  {t.name} ({t.server}) — probability {t.call_probability:.2f}")


@app.command("export")
def export_snapshot(
    task_type: str = typer.Argument(..., help="Task type to export"),
    output: str = typer.Argument(..., help="Output JSON file path"),
    db: str = typer.Option("agentlens.db", help="Path to AgentLens SQLite database"),
) -> None:
    """Export a snapshot to a portable JSON file."""
    asyncio.run(_export_snapshot(task_type, output, db))


@app.command("import")
def import_snapshot(
    path: str = typer.Argument(..., help="Path to snapshot JSON file"),
    db: str = typer.Option("agentlens.db", help="Path to AgentLens SQLite database"),
) -> None:
    """Import snapshots from a portable JSON file into the store."""
    asyncio.run(_import_snapshot(path, db))


async def _export_snapshot(task_type: str, output: str, db: str) -> None:
    from agentlens.snapshot.registry import SnapshotRegistry
    from agentlens.snapshot.store import SnapshotStore
    from agentlens.store.sqlite import SQLiteStore

    store = SQLiteStore(db)
    await store.init()
    ss = SnapshotStore(store)
    snap = await ss.load(task_type)
    await store.close()

    if snap is None:
        console.print(f"[red]No snapshot found for '{task_type}'[/red]")
        raise typer.Exit(1)

    registry = SnapshotRegistry()
    registry.add(snap)
    registry.export(output)
    console.print(f"[green]Exported '{task_type}' snapshot to {output}[/green]")


async def _import_snapshot(path: str, db: str) -> None:
    from agentlens.snapshot.registry import SnapshotRegistry
    from agentlens.snapshot.store import SnapshotStore
    from agentlens.store.sqlite import SQLiteStore

    registry = SnapshotRegistry.import_from(path)
    store = SQLiteStore(db)
    await store.init()
    ss = SnapshotStore(store)

    for snap in registry.all():
        await ss.save(snap)
        console.print(f"[green]Imported snapshot '{snap.task_type}' (confidence {snap.confidence:.2f})[/green]")

    await store.close()
