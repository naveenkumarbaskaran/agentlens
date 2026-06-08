# tests/unit/test_proxy.py
import os
import tempfile
from unittest.mock import MagicMock
import pytest
from agentlens.integrations.mcp.proxy import MCPProxyServer
from agentlens.snapshot.models import SnapshotTool, ToolSnapshot


def _make_mcp_tool(name: str, description: str = "A tool") -> MagicMock:
    tool = MagicMock()
    tool.name = name
    tool.description = description
    tool.inputSchema = {"type": "object", "properties": {}}
    return tool


def test_proxy_filters_tools_with_snapshot():
    upstream_tools = [
        _make_mcp_tool("read_file"),
        _make_mcp_tool("list_dir"),
        _make_mcp_tool("write_file"),
        _make_mcp_tool("delete_file"),
        _make_mcp_tool("run_tests"),
    ]

    snapshot = ToolSnapshot.new(task_type="code-review")
    snapshot.tools = [
        SnapshotTool(name="read_file", server="fs", call_probability=0.95, avg_position=0.0),
        SnapshotTool(name="list_dir",  server="fs", call_probability=0.80, avg_position=1.0),
    ]

    proxy = MCPProxyServer.__new__(MCPProxyServer)
    proxy._optimizer = __import__('agentlens.snapshot.optimizer', fromlist=['ToolOptimizer']).ToolOptimizer()
    selected = proxy._filter_tools(upstream_tools, snapshot)
    assert len(selected) == 2
    assert selected[0].name == "read_file"
    assert selected[1].name == "list_dir"


def test_proxy_exposes_all_tools_without_snapshot():
    upstream_tools = [_make_mcp_tool(n) for n in ["read_file", "list_dir", "write_file"]]

    proxy = MCPProxyServer.__new__(MCPProxyServer)
    proxy._optimizer = __import__('agentlens.snapshot.optimizer', fromlist=['ToolOptimizer']).ToolOptimizer()
    selected = proxy._filter_tools(upstream_tools, snapshot=None)
    assert len(selected) == 3


def test_proxy_compresses_tool_descriptions():
    from agentlens.integrations.mcp.compressor import SchemaCompressor

    proxy = MCPProxyServer.__new__(MCPProxyServer)
    compressor = SchemaCompressor(max_description_chars=200)
    long_desc = "A" * 500
    compressed = proxy._compress_description(long_desc, compressor)
    assert len(compressed) <= 200
    assert compressed.endswith("...")


async def test_proxy_start_stop_lifecycle():
    from agentlens.store.sqlite import SQLiteStore

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        store = SQLiteStore(db_path)
        await store.init()

        proxy = MCPProxyServer(
            upstream_command=["echo", "hello"],
            store=store,
            session_id="test-sess",
            source="test-mcp",
        )
        assert proxy.session_id == "test-sess"
        assert proxy.source == "test-mcp"
    finally:
        await store.close()
        os.unlink(db_path)
