from __future__ import annotations

import asyncio
from typing import Any

import typer
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

app = typer.Typer(help="Live terminal dashboard")
console = Console()


@app.command("show")
def show_dashboard(
    db: str = typer.Option("agentlens.db", help="Path to AgentLens SQLite database"),
    refresh: float = typer.Option(2.0, help="Refresh interval in seconds"),
) -> None:
    """Show live token usage dashboard."""
    asyncio.run(_run_dashboard(db, refresh))


async def _run_dashboard(db: str, refresh: float) -> None:
    from agentlens.store.sqlite import SQLiteStore, _row_to_event

    store = SQLiteStore(db)
    await store.init()

    def _build_layout(stats: dict[str, Any], recent_events: list[Any]) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )
        layout["body"].split_row(
            Layout(name="stats", ratio=1),
            Layout(name="events", ratio=2),
        )

        layout["header"].update(
            Panel(
                Text("AgentLens Dashboard", justify="center", style="bold cyan"),
                border_style="cyan",
            )
        )

        total_in = stats.get("total_input_tokens", 0)
        total_schema = stats.get("total_schema_tokens", 0)
        waste_pct = stats.get("schema_waste_pct", 0.0)
        waste_color = "red" if waste_pct > 30 else "yellow" if waste_pct > 10 else "green"

        stats_text = (
            f"[bold]Sessions (7d):[/bold] {stats.get('total_sessions', 0)}\n"
            f"[bold]Input tokens:[/bold] {total_in:,}\n"
            f"[bold]Output tokens:[/bold] {stats.get('total_output_tokens', 0):,}\n"
            f"[bold]Schema waste:[/bold] [{waste_color}]{total_schema:,} ({waste_pct:.1f}%)[/{waste_color}]\n"
        )
        layout["stats"].update(Panel(stats_text, title="Stats (last 7d)", border_style="blue"))

        table = Table(title="Recent Events", expand=True)
        table.add_column("Kind", style="cyan", width=14)
        table.add_column("Name", style="green")
        table.add_column("Schema tok", justify="right", style="red", width=11)
        table.add_column("Latency", justify="right", width=10)
        table.add_column("Status", width=8)

        for evt in recent_events[-20:]:
            status_str = (
                f"[green]{evt.status.value}[/green]"
                if evt.status.value == "success"
                else f"[red]{evt.status.value}[/red]"
            )
            table.add_row(
                evt.kind.value,
                evt.name[:30],
                str(evt.schema_tokens),
                f"{evt.latency_ms:.0f}ms",
                status_str,
            )

        layout["events"].update(Panel(table, border_style="dim"))
        layout["footer"].update(
            Panel(
                Text(
                    f"Refreshing every {refresh}s  •  Press Ctrl+C to exit",
                    justify="center",
                    style="dim",
                ),
                border_style="dim",
            )
        )
        return layout

    import aiosqlite
    with Live(console=console, refresh_per_second=1, screen=True) as live:
        while True:
            stats = await store.get_recent_stats(days=7)
            async with aiosqlite.connect(store._path) as conn:
                async with conn.execute(
                    "SELECT * FROM events ORDER BY timestamp DESC LIMIT 20"
                ) as cursor:
                    rows = await cursor.fetchall()
            recent = [_row_to_event(row) for row in reversed(list(rows))]  # type: ignore[arg-type]
            live.update(_build_layout(stats, recent))
            await asyncio.sleep(refresh)
