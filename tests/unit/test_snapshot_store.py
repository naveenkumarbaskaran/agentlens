# tests/unit/test_snapshot_store.py
import pytest
from agentlens.snapshot.models import SnapshotTool, ToolSnapshot
from agentlens.snapshot.store import SnapshotStore


async def test_save_and_load_snapshot(store):
    snap = ToolSnapshot.new(task_type="code-review")
    snap.tools = [
        SnapshotTool(name="read_file", server="fs-mcp", call_probability=0.95, avg_position=0.0),
        SnapshotTool(name="list_dir",  server="fs-mcp", call_probability=0.70, avg_position=1.0),
    ]
    snap.confidence = 0.85
    snap.sample_size = 20
    snap.avg_token_savings = 82.5

    ss = SnapshotStore(store)
    await ss.save(snap)

    loaded = await ss.load("code-review")
    assert loaded is not None
    assert loaded.task_type == "code-review"
    assert loaded.confidence == pytest.approx(0.85)
    assert len(loaded.tools) == 2
    assert loaded.tools[0].name == "read_file"
    assert loaded.tools[1].call_probability == pytest.approx(0.70)


async def test_load_missing_returns_none(store):
    ss = SnapshotStore(store)
    result = await ss.load("nonexistent-task")
    assert result is None


async def test_save_overwrites_previous(store):
    ss = SnapshotStore(store)

    snap1 = ToolSnapshot.new(task_type="code-review")
    snap1.tools = [SnapshotTool(name="old_tool", server="srv", call_probability=0.5, avg_position=0.0)]
    snap1.confidence = 0.5
    snap1.sample_size = 5
    snap1.avg_token_savings = 40.0
    await ss.save(snap1)

    snap2 = ToolSnapshot.new(task_type="code-review")
    snap2.tools = [SnapshotTool(name="new_tool", server="srv", call_probability=0.9, avg_position=0.0)]
    snap2.confidence = 0.9
    snap2.sample_size = 20
    snap2.avg_token_savings = 85.0
    await ss.save(snap2)

    loaded = await ss.load("code-review")
    assert loaded is not None
    assert loaded.tools[0].name == "new_tool"
    assert loaded.confidence == pytest.approx(0.9)
