"""
Basic AgentLens example: wrap an Anthropic client and profile a single call.

Run: python examples/anthropic_basic.py
"""
import asyncio
import anthropic
from agentlens import AgentLens


async def main() -> None:
    lens = AgentLens(store="sqlite:///agentlens_example.db")
    await lens.init()

    raw_client = anthropic.Anthropic()

    async with lens.session(agent_id="example-agent", task_type="qa") as sess:
        client = lens.wrap_anthropic(session=sess)

        async def _real_call(**kwargs):  # type: ignore
            return raw_client.messages.create(model="claude-haiku-4-5-20251001", **kwargs)

        client._call_upstream = _real_call  # type: ignore

        response = await client.messages_create(
            messages=[{"role": "user", "content": "What is 6 times 7?"}],
            max_tokens=50,
        )
        print(response.content[0].text)

    print(f"Session {sess.session_id} complete.")
    print(f"  Input tokens:  {sess.total_input_tokens}")
    print(f"  Output tokens: {sess.total_output_tokens}")
    print(f"  Cost USD:      ${sess.total_cost_usd:.6f}")

    await lens.close()


if __name__ == "__main__":
    asyncio.run(main())
