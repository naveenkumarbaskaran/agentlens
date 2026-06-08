import pytest


@pytest.mark.asyncio
async def test_lens_wrap_openai(tmp_path):
    from agentlens.lens import AgentLens
    from agentlens.integrations.openai import LensOpenAIClient

    db = str(tmp_path / "lens.db")
    lens = AgentLens(store=f"sqlite:///{db}")
    await lens.init()

    async with lens.session(agent_id="agent-oai") as sess:
        client = lens.wrap_openai(session=sess)
        assert isinstance(client, LensOpenAIClient)
        assert client.session_id == sess.session_id

    await lens.close()
