# tests/unit/test_registry.py
import json
import pytest
from agentlens.snapshot.models import SnapshotTool, ToolSnapshot
from agentlens.snapshot.registry import SnapshotRegistry


def _make_snapshot(task_type: str) -> ToolSnapshot:
    snap = ToolSnapshot.new(task_type=task_type)
    snap.tools = [
        SnapshotTool(name="read_file", server="fs-mcp", call_probability=0.9, avg_position=0.0),
        SnapshotTool(name="list_dir",  server="fs-mcp", call_probability=0.7, avg_position=1.0),
    ]
    snap.confidence = 0.85
    snap.sample_size = 20
    snap.avg_token_savings = 82.5
    snap.tags = ["filesystem", "code"]
    return snap


def test_export_produces_valid_json(tmp_path):
    registry = SnapshotRegistry()
    snap = _make_snapshot("code-review")
    registry.add(snap)

    out_path = tmp_path / "snapshots.json"
    registry.export(str(out_path))

    with open(out_path) as f:
        data = json.load(f)

    assert data["version"] == 1
    assert len(data["snapshots"]) == 1
    assert data["snapshots"][0]["task_type"] == "code-review"
    assert len(data["snapshots"][0]["tools"]) == 2


def test_import_round_trip(tmp_path):
    registry = SnapshotRegistry()
    snap = _make_snapshot("code-review")
    registry.add(snap)

    out_path = tmp_path / "snapshots.json"
    registry.export(str(out_path))

    loaded_registry = SnapshotRegistry.import_from(str(out_path))
    snaps = loaded_registry.all()
    assert len(snaps) == 1
    assert snaps[0].task_type == "code-review"
    assert snaps[0].tools[0].name == "read_file"
    assert snaps[0].confidence == pytest.approx(0.85)
    assert snaps[0].tags == ["filesystem", "code"]


def test_export_multiple_snapshots(tmp_path):
    registry = SnapshotRegistry()
    registry.add(_make_snapshot("code-review"))
    registry.add(_make_snapshot("db-query"))

    out_path = tmp_path / "multi.json"
    registry.export(str(out_path))

    loaded = SnapshotRegistry.import_from(str(out_path))
    task_types = {s.task_type for s in loaded.all()}
    assert task_types == {"code-review", "db-query"}


def test_get_by_task_type(tmp_path):
    registry = SnapshotRegistry()
    registry.add(_make_snapshot("code-review"))
    registry.add(_make_snapshot("db-query"))

    result = registry.get("code-review")
    assert result is not None
    assert result.task_type == "code-review"

    missing = registry.get("nonexistent")
    assert missing is None
