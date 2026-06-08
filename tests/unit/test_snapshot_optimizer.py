from agentlens.snapshot.models import SnapshotTool, ToolSnapshot
from agentlens.snapshot.optimizer import ToolOptimizer


def _snapshot(tool_names: list[str]) -> ToolSnapshot:
    snap = ToolSnapshot.new(task_type="code-review")
    snap.tools = [
        SnapshotTool(name=n, server="srv", call_probability=0.9, avg_position=i)
        for i, n in enumerate(tool_names)
    ]
    return snap


def test_filter_tools_by_snapshot():
    snapshot = _snapshot(["read_file", "list_dir"])
    all_tools = ["read_file", "list_dir", "write_file", "delete_file", "run_tests"]
    optimizer = ToolOptimizer()
    selected = optimizer.select_tools(all_tools, snapshot)
    assert selected == ["read_file", "list_dir"]
    assert "write_file" not in selected


def test_select_tools_preserves_snapshot_order():
    snapshot = _snapshot(["list_dir", "read_file"])  # list_dir first
    all_tools = ["read_file", "list_dir", "write_file"]
    optimizer = ToolOptimizer()
    selected = optimizer.select_tools(all_tools, snapshot)
    assert selected[0] == "list_dir"
    assert selected[1] == "read_file"
