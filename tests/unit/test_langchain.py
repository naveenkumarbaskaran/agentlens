# tests/unit/test_langchain.py
import pytest
from unittest.mock import MagicMock
from agentlens.integrations.langchain import LangChainLensCallback
from agentlens.core.events import EventKind, EventStatus


async def test_langchain_callback_records_llm_call(store):
    cb = LangChainLensCallback(
        store=store,
        session_id="lc-sess-1",
        model="claude-sonnet-4-6",
    )

    run_id = "run-abc"
    await cb.on_llm_start(
        serialized={"name": "ChatAnthropic"},
        prompts=["What is 2+2?"],
        run_id=run_id,
    )

    mock_response = MagicMock()
    mock_response.generations = [[
        MagicMock(
            text="4",
            message=MagicMock(
                usage_metadata={"input_tokens": 20, "output_tokens": 5}
            )
        )
    ]]
    await cb.on_llm_end(response=mock_response, run_id=run_id)

    events = await store.get_events_for_session("lc-sess-1")
    assert len(events) == 1
    assert events[0].kind == EventKind.LLM_CALL
    assert events[0].input_tokens == 20
    assert events[0].output_tokens == 5
    assert events[0].status == EventStatus.SUCCESS


async def test_langchain_callback_records_tool_call(store):
    cb = LangChainLensCallback(
        store=store,
        session_id="lc-sess-2",
        model="claude-sonnet-4-6",
    )

    run_id = "tool-run-xyz"
    await cb.on_tool_start(
        serialized={"name": "read_file"},
        input_str='{"path": "/src/main.py"}',
        run_id=run_id,
    )
    await cb.on_tool_end(output="file contents here", run_id=run_id)

    events = await store.get_events_for_session("lc-sess-2")
    assert len(events) == 1
    assert events[0].kind == EventKind.TOOL_CALL
    assert events[0].name == "read_file"
    assert events[0].status == EventStatus.SUCCESS


async def test_langchain_callback_records_tool_error(store):
    cb = LangChainLensCallback(
        store=store,
        session_id="lc-sess-3",
        model="claude-sonnet-4-6",
    )

    run_id = "tool-err-xyz"
    await cb.on_tool_start(
        serialized={"name": "read_file"},
        input_str='{"path": "/missing.py"}',
        run_id=run_id,
    )
    await cb.on_tool_error(error=ValueError("file not found"), run_id=run_id)

    events = await store.get_events_for_session("lc-sess-3")
    assert len(events) == 1
    assert events[0].status == EventStatus.FAILURE
    assert "file not found" in (events[0].error or "")
