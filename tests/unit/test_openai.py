# tests/unit/test_openai.py
import pytest
from unittest.mock import MagicMock, patch
from agentlens.core.events import EventKind, EventStatus
from agentlens.integrations.openai import LensOpenAIClient
from agentlens.profiler.enricher import TokenEnricher


async def test_openai_call_recorded(store):
    enricher = TokenEnricher(model="claude-sonnet-4-6")
    client = LensOpenAIClient(
        session_id="oai-sess-1",
        store=store,
        enricher=enricher,
        model="gpt-4o",
    )

    mock_response = MagicMock()
    mock_response.usage.prompt_tokens = 120
    mock_response.usage.completion_tokens = 60
    mock_response.choices = [MagicMock(message=MagicMock(content="Hello!"))]

    with patch.object(client, "_call_upstream", return_value=mock_response):
        response = await client.chat_completions_create(
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=50,
        )

    events = await store.get_events_for_session("oai-sess-1")
    assert len(events) == 1
    assert events[0].kind == EventKind.LLM_CALL
    assert events[0].input_tokens == 120
    assert events[0].output_tokens == 60
    assert events[0].name == "gpt-4o"
    assert events[0].source == "openai"


async def test_openai_cost_in_metadata(store):
    enricher = TokenEnricher(model="claude-sonnet-4-6")
    client = LensOpenAIClient(
        session_id="oai-sess-2",
        store=store,
        enricher=enricher,
        model="gpt-4o",
        input_cost_per_m=2.50,
        output_cost_per_m=10.0,
    )

    mock_response = MagicMock()
    mock_response.usage.prompt_tokens = 1_000_000
    mock_response.usage.completion_tokens = 0
    mock_response.choices = [MagicMock(message=MagicMock(content="x"))]

    with patch.object(client, "_call_upstream", return_value=mock_response):
        await client.chat_completions_create(
            messages=[{"role": "user", "content": "x"}],
            max_tokens=1,
        )

    events = await store.get_events_for_session("oai-sess-2")
    assert events[0].metadata["cost_usd"] == pytest.approx(2.50, rel=0.01)


async def test_openai_failure_recorded(store):
    enricher = TokenEnricher()
    client = LensOpenAIClient(
        session_id="oai-sess-3",
        store=store,
        enricher=enricher,
        model="gpt-4o",
    )

    with patch.object(client, "_call_upstream", side_effect=RuntimeError("rate limited")):
        with pytest.raises(RuntimeError):
            await client.chat_completions_create(
                messages=[{"role": "user", "content": "x"}],
                max_tokens=1,
            )

    events = await store.get_events_for_session("oai-sess-3")
    assert events[0].status == EventStatus.FAILURE
    assert "rate limited" in (events[0].error or "")
