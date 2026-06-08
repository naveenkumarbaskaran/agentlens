from __future__ import annotations

import asyncio
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Inspect recorded sessions and traces")
console = Console()


@app.command("show")
def show_session(
    session_id: str = typer.Argument(..., help="Session ID to inspect"),
    db: str = typer.Option("agentlens.db", help="Path to AgentLens SQLite database"),
) -> None:
    """Show all events for a session."""
    asyncio.run(_show_session(session_id, db))


async def _show_session(session_id: str, db: str) -> None:
    from agentlens.store.sqlite import SQLiteStore

    store = SQLiteStore(db)
    await store.init()
    events = await store.get_events_for_session(session_id)
    await store.close()

    if not events:
        console.print(f"[yellow]No events found for session {session_id}[/yellow]")
        raise typer.Exit(1)

    table = Table(title=f"Session: {session_id}")
    table.add_column("Kind", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Source")
    table.add_column("In Tokens", justify="right")
    table.add_column("Out Tokens", justify="right")
    table.add_column("Schema Tokens", justify="right", style="red")
    table.add_column("Latency ms", justify="right")
    table.add_column("Status")

    for evt in events:
        table.add_row(
            evt.kind.value,
            evt.name,
            evt.source,
            str(evt.input_tokens),
            str(evt.output_tokens),
            str(evt.schema_tokens),
            f"{evt.latency_ms:.1f}",
            f"[green]{evt.status.value}[/green]"
            if evt.status.value == "success"
            else f"[red]{evt.status.value}[/red]",
        )

    console.print(table)
