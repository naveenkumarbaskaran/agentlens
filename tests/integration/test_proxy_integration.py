# tests/integration/test_proxy_integration.py
"""
End-to-end proxy test using an in-process FastMCP server as the upstream.
Spawns a tiny Python subprocess that serves one tool via stdio.
"""
import sys
import pytest
from agentlens.core.events import EventKind
from agentlens.store.sqlite import SQLiteStore


async def test_proxy_profiles_tool_calls(tmp_path):
    """
    Spawn a tiny upstream MCP server as a Python subprocess, call one tool
    through MCPInterceptor, and verify a LensEvent was stored.
    """
    from mcp import ClientSession, StdioServerParameters, stdio_client
    from agentlens.integrations.mcp.interceptor import MCPInterceptor
    from agentlens.profiler.enricher import TokenEnricher

    db_path = str(tmp_path / "proxy.db")
    store = SQLiteStore(db_path)
    await store.init()

    session_id = "proxy-test-session"

    # Write a tiny upstream MCP server to a temp file
    upstream_script = tmp_path / "upstream.py"
    upstream_script.write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "import asyncio\n"
        "fmcp = FastMCP('test-upstream')\n"
        "\n"
        "@fmcp.tool()\n"
        "def echo(message: str) -> str:\n"
        "    return f'echo:{message}'\n"
        "\n"
        "asyncio.run(fmcp.run_stdio_async())\n"
    )

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(upstream_script)],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as upstream:
            await upstream.initialize()
            tools_result = await upstream.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            assert "echo" in tool_names

            enricher = TokenEnricher()
            interceptor = MCPInterceptor(
                session_id=session_id, store=store, enricher=enricher
            )

            async def _call_upstream(name: str, arguments: dict) -> object:
                return await upstream.call_tool(name, arguments)

            interceptor._call_tool_upstream = _call_upstream  # type: ignore[method-assign]

            await interceptor.call_tool(
                name="echo",
                arguments={"message": "hello"},
                source="test-upstream",
            )

    events = await store.get_events_for_session(session_id)
    assert len(events) == 1
    assert events[0].kind == EventKind.TOOL_CALL
    assert events[0].name == "echo"
    assert events[0].status.value == "success"

    await store.close()
