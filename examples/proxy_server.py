"""
Proxy example: run AgentLens as a transparent MCP proxy.
Agents connect to this proxy instead of the real MCP server — zero agent code changes.

Usage via CLI:
    agentlens proxy start --upstream "uvx mcp-server-filesystem /tmp"

With snapshot filtering (only loads the tools that matter for code-review):
    agentlens proxy start --upstream "uvx mcp-server-filesystem /tmp" --task-type code-review

Programmatic usage (this script):
    python examples/proxy_server.py
"""
import asyncio
from agentlens.integrations.mcp.proxy import MCPProxyServer
from agentlens.store.sqlite import SQLiteStore


async def main() -> None:
    store = SQLiteStore("agentlens_proxy.db")
    await store.init()

    proxy = MCPProxyServer(
        upstream_command=["uvx", "mcp-server-filesystem", "/tmp"],
        store=store,
        source="filesystem-mcp",
        # Optionally load a snapshot to restrict to known-useful tools:
        # snapshot=snapshot,
    )

    print("AgentLens proxy running on stdio.")
    print("Point your agent at this proxy instead of the real MCP server.")
    print("All tool calls will be profiled in agentlens_proxy.db")
    await proxy.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
