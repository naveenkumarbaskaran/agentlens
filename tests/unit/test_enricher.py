# tests/unit/test_enricher.py
import pytest
from agentlens.profiler.enricher import TokenEnricher


def test_count_tokens_string():
    enricher = TokenEnricher(model="gpt-4o")
    count = enricher.count_tokens("Hello, world!")
    assert isinstance(count, int)
    assert count > 0


def test_count_tokens_dict():
    enricher = TokenEnricher(model="gpt-4o")
    schema = {"type": "object", "properties": {"name": {"type": "string", "description": "The name of the tool"}}}
    count = enricher.count_schema_tokens(schema)
    assert count > 0


def test_estimate_cost_sonnet():
    enricher = TokenEnricher(model="claude-sonnet-4-6")
    cost = enricher.estimate_cost(input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == pytest.approx(18.0, rel=0.01)


def test_estimate_cost_haiku():
    enricher = TokenEnricher(model="claude-haiku-4-5-20251001")
    cost = enricher.estimate_cost(input_tokens=1_000_000, output_tokens=1_000_000)
    # haiku: $0.80/M input, $4/M output
    assert cost == pytest.approx(4.8, rel=0.01)
