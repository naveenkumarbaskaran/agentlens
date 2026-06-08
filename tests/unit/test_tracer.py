# tests/unit/test_tracer.py
import pytest
from agentlens.core.context import current_session
from agentlens.core.session import LensSession, SessionManager


def test_session_accumulates_tokens():
    sess = LensSession(session_id="s1", agent_id="agent-a", framework="raw")
    sess.add_tokens(input_tokens=100, output_tokens=50, schema_tokens=200)
    sess.add_tokens(input_tokens=80, output_tokens=30, schema_tokens=150)
    assert sess.total_input_tokens == 180
    assert sess.total_output_tokens == 80
    assert sess.total_schema_tokens == 350


def test_session_cost_usd():
    sess = LensSession(session_id="s1", agent_id="agent-a", framework="raw")
    # claude-sonnet-4-6: $3/M input, $15/M output
    sess.add_tokens(input_tokens=1_000_000, output_tokens=1_000_000, schema_tokens=0)
    assert sess.total_cost_usd == pytest.approx(18.0, rel=0.01)


async def test_session_manager_context():
    manager = SessionManager()
    async with manager.session(agent_id="agent-a", framework="raw") as sess:
        token = current_session.get()
        assert token is sess
        assert sess.session_id is not None
    # after context, session is no longer current
    assert current_session.get(None) is None
