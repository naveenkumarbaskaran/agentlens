# tests/unit/test_predictive.py
from unittest.mock import AsyncMock, patch
import pytest
from agentlens.lens import AgentLens


async def test_lens_classify_task_returns_type(tmp_path):
    db = str(tmp_path / "lens.db")
    lens = AgentLens(store=f"sqlite:///{db}")
    await lens.init()

    with patch(
        "agentlens.profiler.classifier.TaskClassifier.classify",
        new=AsyncMock(return_value="code-review"),
    ):
        result = await lens.classify_task(
            message="Please review this pull request",
            known_task_types=["code-review", "db-query"],
        )

    assert result == "code-review"
    await lens.close()


async def test_lens_classify_task_returns_none_when_unrecognized(tmp_path):
    db = str(tmp_path / "lens.db")
    lens = AgentLens(store=f"sqlite:///{db}")
    await lens.init()

    with patch(
        "agentlens.profiler.classifier.TaskClassifier.classify",
        new=AsyncMock(return_value=None),
    ):
        result = await lens.classify_task(
            message="What is the capital of France?",
            known_task_types=["code-review", "db-query"],
        )

    assert result is None
    await lens.close()
