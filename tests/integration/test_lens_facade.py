# tests/integration/test_lens_facade.py
import pytest
from agentlens.lens import AgentLens


async def test_lens_session_context(tmp_path):
    db = str(tmp_path / "lens.db")
    lens = AgentLens(store=f"sqlite:///{db}")
    await lens.init()

    async with lens.session(agent_id="my-agent", task_type="code-review") as sess:
        assert sess.session_id is not None
        assert sess.framework == "raw"

    await lens.close()


async def test_lens_creates_mcp_interceptor(tmp_path):
    db = str(tmp_path / "lens.db")
    lens = AgentLens(store=f"sqlite:///{db}")
    await lens.init()

    async with lens.session(agent_id="agent-b") as sess:
        interceptor = lens.wrap_mcp(session=sess, source="my-mcp")
        assert interceptor is not None

    await lens.close()
