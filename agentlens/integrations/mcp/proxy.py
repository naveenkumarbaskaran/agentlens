from __future__ import annotations

import uuid
from typing import Any

from agentlens.integrations.mcp.compressor import SchemaCompressor
from agentlens.integrations.mcp.interceptor import MCPInterceptor
from agentlens.profiler.enricher import TokenEnricher
from agentlens.snapshot.models import ToolSnapshot
from agentlens.snapshot.optimizer import ToolOptimizer
from agentlens.store.base import AbstractStore


class MCPProxyServer:
    """
    Transparent MCP proxy. Connects to an upstream MCP server via subprocess,
    fetches its tools, optionally filters using a snapshot, re-exposes the
    reduced tool set as a FastMCP server, and profiles every call.

    Usage (stdio):
        proxy = MCPProxyServer(
            upstream_command=["uvx", "mcp-server-filesystem", "/tmp"],
            store=store,
            session_id="sess-abc",
            source="filesystem-mcp",
            snapshot=snapshot,
        )
        await proxy.run_stdio()

    Usage (HTTP):
        await proxy.run_http(host="127.0.0.1", port=3100)
    """

    def __init__(
        self,
        upstream_command: list[str],
        store: AbstractStore,
        session_id: str | None = None,
        source: str = "upstream-mcp",
        snapshot: ToolSnapshot | None = None,
        max_description_chars: int = 200,
        model: str = "claude-sonnet-4-6",
    ) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.source = source
        self._upstream_command = upstream_command
        self._store = store
        self._snapshot = snapshot
        self._compressor = SchemaCompressor(max_description_chars=max_description_chars)
        self._optimizer = ToolOptimizer()
        self._enricher = TokenEnricher(model=model)
        self._interceptor = MCPInterceptor(
            session_id=self.session_id,
            store=store,
            enricher=self._enricher,
        )

    # ── tool filtering helpers ──────────────────────────────────────────────

    def _filter_tools(
        self,
        upstream_tools: list[Any],
        snapshot: ToolSnapshot | None,
    ) -> list[Any]:
        if snapshot is None:
            return upstream_tools
        allowed = set(self._optimizer.select_tools(
            [t.name for t in upstream_tools], snapshot
        ))
        # Preserve snapshot ordering
        ordered_names = [t.name for t in snapshot.tools if t.name in allowed]
        by_name = {t.name: t for t in upstream_tools}
        return [by_name[n] for n in ordered_names if n in by_name]

    def _compress_description(self, description: str, compressor: SchemaCompressor) -> str:
        result = compressor.compress({"description": description})
        return result["description"]

    # ── runtime ────────────────────────────────────────────────────────────

    async def run_stdio(self) -> None:
        """Fetch upstream tools, build a FastMCP proxy, and serve on stdio."""
        from mcp import ClientSession, StdioServerParameters, stdio_client
        from mcp.server.fastmcp import FastMCP

        params = StdioServerParameters(
            command=self._upstream_command[0],
            args=self._upstream_command[1:],
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as upstream:
                await upstream.initialize()
                tools_result = await upstream.list_tools()
                selected_tools = self._filter_tools(tools_result.tools, self._snapshot)

                fmcp = FastMCP(name=f"agentlens-proxy:{self.source}")
                self._register_tools(fmcp, selected_tools, upstream)
                await fmcp.run_stdio_async()

    async def run_http(self, host: str = "127.0.0.1", port: int = 3100) -> None:
        """Serve the proxy over streamable HTTP."""
        from mcp import ClientSession, StdioServerParameters, stdio_client
        from mcp.server.fastmcp import FastMCP

        params = StdioServerParameters(
            command=self._upstream_command[0],
            args=self._upstream_command[1:],
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as upstream:
                await upstream.initialize()
                tools_result = await upstream.list_tools()
                selected_tools = self._filter_tools(tools_result.tools, self._snapshot)

                fmcp = FastMCP(name=f"agentlens-proxy:{self.source}", host=host, port=port)
                self._register_tools(fmcp, selected_tools, upstream)
                await fmcp.run_streamable_http_async()

    def _register_tools(self, fmcp: Any, tools: list[Any], upstream: Any) -> None:
        """Register each selected tool on the FastMCP server with profiled forwarding."""
        interceptor = self._interceptor
        source = self.source
        compressor = self._compressor

        for tool in tools:
            tool_name = tool.name
            compressed_desc = self._compress_description(tool.description or "", compressor)

            # Capture loop variable correctly via default argument
            async def _upstream_call(
                name: str = tool_name,
                arguments: dict[str, Any] = {},
                _up: Any = upstream,
            ) -> Any:
                return await _up.call_tool(name, arguments)

            interceptor._call_tool_upstream = _upstream_call  # type: ignore[method-assign]

            async def _handler(
                _name: str = tool_name,
                _interceptor: MCPInterceptor = interceptor,
                _source: str = source,
                **kwargs: Any,
            ) -> Any:
                return await _interceptor.call_tool(
                    name=_name,
                    arguments=kwargs,
                    source=_source,
                )

            fmcp.add_tool(_handler, name=tool_name, description=compressed_desc)
