# tests/integration/test_mcp_interceptor.py
from unittest.mock import MagicMock, patch
import pytest
from agentlens.core.events import EventKind, EventStatus
from agentlens.integrations.mcp.interceptor import MCPInterceptor
from agentlens.profiler.enricher import TokenEnricher


async def test_interceptor_records_tool_call(store):
    enricher = TokenEnricher()
    interceptor = MCPInterceptor(
        session_id="sess-1",
        store=store,
        enricher=enricher,
    )

    mock_result = MagicMock()
    mock_result.content = [MagicMock(text="file contents here")]

    with patch.object(interceptor, "_call_tool_upstream", return_value=mock_result):
        result = await interceptor.call_tool(
            name="read_file",
            arguments={"path": "/src/main.py"},
            source="filesystem-mcp",
        )

    events = await store.get_events_for_session("sess-1")
    assert len(events) == 1
    assert events[0].kind == EventKind.TOOL_CALL
    assert events[0].name == "read_file"
    assert events[0].status == EventStatus.SUCCESS


async def test_interceptor_records_failure(store):
    enricher = TokenEnricher()
    interceptor = MCPInterceptor(
        session_id="sess-2",
        store=store,
        enricher=enricher,
    )

    with patch.object(interceptor, "_call_tool_upstream", side_effect=RuntimeError("not found")):
        with pytest.raises(RuntimeError):
            await interceptor.call_tool(
                name="read_file",
                arguments={"path": "/missing.py"},
                source="filesystem-mcp",
            )

    events = await store.get_events_for_session("sess-2")
    assert events[0].status == EventStatus.FAILURE
    assert "not found" in (events[0].error or "")
