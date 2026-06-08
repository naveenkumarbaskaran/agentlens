# tests/integration/test_anthropic_wrapper.py
from unittest.mock import MagicMock, patch
import pytest
from agentlens.core.events import EventKind
from agentlens.integrations.anthropic import LensAnthropicClient
from agentlens.profiler.enricher import TokenEnricher


async def test_llm_call_recorded(store):
    enricher = TokenEnricher(model="claude-sonnet-4-6")
    client = LensAnthropicClient(
        session_id="sess-1",
        store=store,
        enricher=enricher,
        model="claude-sonnet-4-6",
    )

    mock_response = MagicMock()
    mock_response.usage.input_tokens = 150
    mock_response.usage.output_tokens = 80
    mock_response.content = [MagicMock(text="The answer is 42.")]

    with patch.object(client, "_call_upstream", return_value=mock_response):
        response = await client.messages_create(
            messages=[{"role": "user", "content": "What is 6x7?"}],
            max_tokens=100,
        )

    events = await store.get_events_for_session("sess-1")
    assert len(events) == 1
    assert events[0].kind == EventKind.LLM_CALL
    assert events[0].input_tokens == 150
    assert events[0].output_tokens == 80
    assert events[0].name == "claude-sonnet-4-6"


async def test_cost_recorded_in_event(store):
    enricher = TokenEnricher(model="claude-sonnet-4-6")
    client = LensAnthropicClient(
        session_id="sess-2",
        store=store,
        enricher=enricher,
        model="claude-sonnet-4-6",
    )
    mock_response = MagicMock()
    mock_response.usage.input_tokens = 1_000_000
    mock_response.usage.output_tokens = 0
    mock_response.content = [MagicMock(text="x")]

    with patch.object(client, "_call_upstream", return_value=mock_response):
        await client.messages_create(
            messages=[{"role": "user", "content": "x"}],
            max_tokens=1,
        )

    events = await store.get_events_for_session("sess-2")
    assert events[0].metadata["cost_usd"] == pytest.approx(3.0, rel=0.01)
