# tests/unit/test_events.py
from datetime import datetime, timezone
import pytest
from agentlens.core.events import EventKind, EventStatus, LensEvent


def test_lens_event_defaults():
    event = LensEvent(
        event_id="evt-001",
        session_id="sess-001",
        trace_id="trace-001",
        span_id="span-001",
        parent_span_id=None,
        kind=EventKind.TOOL_CALL,
        source="my-mcp-server",
        name="read_file",
        input_tokens=100,
        output_tokens=50,
        schema_tokens=200,
        latency_ms=42.5,
        status=EventStatus.SUCCESS,
        error=None,
        task_type="code-review",
        metadata={},
        timestamp=datetime.now(timezone.utc),
    )
    assert event.kind == EventKind.TOOL_CALL
    assert event.schema_tokens == 200
    assert event.parent_span_id is None


def test_event_kind_values():
    assert EventKind.TOOL_CALL.value == "tool_call"
    assert EventKind.MCP_SCHEMA_LOAD.value == "mcp_schema_load"
    assert EventKind.AGENT_INVOKE.value == "agent_invoke"
    assert EventKind.LLM_CALL.value == "llm_call"


def test_event_status_values():
    assert EventStatus.SUCCESS.value == "success"
    assert EventStatus.FAILURE.value == "failure"
    assert EventStatus.TIMEOUT.value == "timeout"
    assert EventStatus.SKIPPED.value == "skipped"


def test_lens_event_total_tokens():
    event = LensEvent(
        event_id="e", session_id="s", trace_id="t", span_id="sp",
        parent_span_id=None, kind=EventKind.LLM_CALL, source="claude",
        name="claude-sonnet-4-6", input_tokens=500, output_tokens=200,
        schema_tokens=300, latency_ms=1200.0, status=EventStatus.SUCCESS,
        error=None, task_type=None, metadata={},
        timestamp=datetime.now(timezone.utc),
    )
    assert event.total_tokens == 700  # input + output, not schema
