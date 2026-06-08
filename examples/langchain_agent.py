"""
LangChain example: profile a LangChain agent using LangChainLensCallback.

Run:
    pip install langchain-core langchain-anthropic
    python examples/langchain_agent.py
"""
import asyncio
from unittest.mock import MagicMock
from agentlens.integrations.langchain import LangChainLensCallback
from agentlens.store.sqlite import SQLiteStore


async def main() -> None:
    store = SQLiteStore("agentlens_langchain.db")
    await store.init()

    cb = LangChainLensCallback(
        store=store,
        session_id="langchain-demo",
        model="claude-sonnet-4-6",
        task_type="qa",
    )

    # Simulate the LangChain callback lifecycle
    run_id = "demo-run-001"

    await cb.on_llm_start(
        serialized={"name": "ChatAnthropic"},
        prompts=["What is the capital of France?"],
        run_id=run_id,
    )

    # Simulate LLM response (in a real app, LangChain calls this automatically)
    mock_response = MagicMock()
    mock_response.generations = [[
        MagicMock(
            text="Paris",
            message=MagicMock(
                usage_metadata={"input_tokens": 25, "output_tokens": 3}
            )
        )
    ]]
    await cb.on_llm_end(response=mock_response, run_id=run_id)

    events = await store.get_events_for_session("langchain-demo")
    print(f"Recorded {len(events)} event(s):")
    for evt in events:
        print(
            f"  {evt.kind.value}: {evt.name}"
            f" — {evt.input_tokens} in / {evt.output_tokens} out tokens"
            f" — cost: ${evt.metadata.get('cost_usd', 0):.6f}"
        )

    await store.close()


if __name__ == "__main__":
    asyncio.run(main())
