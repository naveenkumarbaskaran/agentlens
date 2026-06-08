from __future__ import annotations

import asyncio
import shlex

import typer
from rich.console import Console

app = typer.Typer(help="MCP proxy server")
console = Console()


@app.command("start")
def start_proxy(
    upstream: str = typer.Option(..., help="Upstream MCP command, e.g. 'uvx mcp-server-filesystem /tmp'"),
    port: int = typer.Option(0, help="HTTP port (0 = stdio mode)"),
    task_type: str = typer.Option("", help="Task type to load snapshot for (optional)"),
    db: str = typer.Option("agentlens.db", help="Path to AgentLens SQLite database"),
) -> None:
    """Start a transparent MCP proxy in front of an upstream MCP server."""
    asyncio.run(_run_proxy(upstream, port, task_type or None, db))


async def _run_proxy(
    upstream: str,
    port: int,
    task_type: str | None,
    db: str,
) -> None:
    from agentlens.integrations.mcp.proxy import MCPProxyServer
    from agentlens.snapshot.store import SnapshotStore
    from agentlens.store.sqlite import SQLiteStore

    store = SQLiteStore(db)
    await store.init()

    snapshot = None
    if task_type:
        ss = SnapshotStore(store)
        snapshot = await ss.load(task_type)
        if snapshot:
            console.print(
                f"[green]Loaded snapshot '{task_type}': "
                f"{len(snapshot.tools)} tools, confidence {snapshot.confidence:.2f}[/green]"
            )
        else:
            console.print(
                f"[yellow]No snapshot found for '{task_type}' — exposing all tools[/yellow]"
            )

    cmd = shlex.split(upstream)
    proxy = MCPProxyServer(
        upstream_command=cmd,
        store=store,
        source=cmd[0],
        snapshot=snapshot,
    )

    if port > 0:
        console.print(f"[cyan]Starting AgentLens proxy on http://127.0.0.1:{port}[/cyan]")
        await proxy.run_http(host="127.0.0.1", port=port)
    else:
        console.print("[cyan]Starting AgentLens proxy on stdio[/cyan]")
        await proxy.run_stdio()
