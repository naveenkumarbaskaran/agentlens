from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(help="Token cost and usage statistics")
console = Console()


@app.command("show")
def show_stats(
    last: str = typer.Option("7d", help="Time window: 1d, 7d, 30d"),
    db: str = typer.Option("agentlens.db", help="Path to AgentLens SQLite database"),
) -> None:
    """Show token usage and cost breakdown."""
    asyncio.run(_show_stats(last, db))


async def _show_stats(last: str, db: str) -> None:
    import aiosqlite
    from agentlens.store.sqlite import SQLiteStore

    days = int(last.rstrip("d"))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    store = SQLiteStore(db)
    await store.init()
    await store.close()

    async with aiosqlite.connect(db) as conn:
        async with conn.execute(
            "SELECT SUM(input_tokens), SUM(output_tokens), SUM(schema_tokens), COUNT(DISTINCT session_id) "
            "FROM events WHERE timestamp >= ?",
            (cutoff.isoformat(),),
        ) as cursor:
            row = await cursor.fetchone()

    if row is None or row[0] is None:
        console.print("[yellow]No data found for this time window.[/yellow]")
        return

    total_in, total_out, total_schema, sessions = row
    schema_pct = (total_schema / (total_in + total_schema)) * 100 if total_in else 0

    console.print(
        Panel(
            f"[bold]Sessions:[/bold] {sessions}\n"
            f"[bold]Input tokens:[/bold] {total_in:,}\n"
            f"[bold]Output tokens:[/bold] {total_out:,}\n"
            f"[bold cyan]Schema tokens (waste):[/bold cyan] {total_schema:,} ({schema_pct:.1f}% of input)\n",
            title=f"AgentLens Stats — last {last}",
            border_style="blue",
        )
    )
