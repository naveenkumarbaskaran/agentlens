from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from agentlens.snapshot.models import SnapshotTool, ToolSnapshot

_REGISTRY_VERSION = 1


class SnapshotRegistry:
    """
    Portable snapshot bundle — export/import ToolSnapshots as a JSON file.

    Usage:
        # Export
        registry = SnapshotRegistry()
        registry.add(snapshot)
        registry.export("my_snapshots.json")

        # Import
        registry = SnapshotRegistry.import_from("my_snapshots.json")
        snap = registry.get("code-review")
    """

    def __init__(self) -> None:
        self._snapshots: dict[str, ToolSnapshot] = {}

    def add(self, snapshot: ToolSnapshot) -> None:
        self._snapshots[snapshot.task_type] = snapshot

    def get(self, task_type: str) -> ToolSnapshot | None:
        return self._snapshots.get(task_type)

    def all(self) -> list[ToolSnapshot]:
        return list(self._snapshots.values())

    def export(self, path: str) -> None:
        data: dict[str, Any] = {
            "version": _REGISTRY_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "snapshots": [_snapshot_to_dict(s) for s in self._snapshots.values()],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def import_from(cls, path: str) -> "SnapshotRegistry":
        with open(path) as f:
            data = json.load(f)
        registry = cls()
        for snap_dict in data.get("snapshots", []):
            registry.add(_dict_to_snapshot(snap_dict))
        return registry


def _snapshot_to_dict(snap: ToolSnapshot) -> dict[str, Any]:
    return {
        "snapshot_id": snap.snapshot_id,
        "task_type": snap.task_type,
        "version": snap.version,
        "confidence": snap.confidence,
        "sample_size": snap.sample_size,
        "avg_token_savings": snap.avg_token_savings,
        "tags": snap.tags,
        "created_at": snap.created_at.isoformat(),
        "tools": [
            {
                "name": t.name,
                "server": t.server,
                "call_probability": t.call_probability,
                "avg_position": t.avg_position,
                "compressed_schema": t.compressed_schema,
            }
            for t in snap.tools
        ],
    }


def _dict_to_snapshot(d: dict[str, Any]) -> ToolSnapshot:
    tools = [
        SnapshotTool(
            name=t["name"],
            server=t["server"],
            call_probability=t["call_probability"],
            avg_position=t["avg_position"],
            compressed_schema=t.get("compressed_schema", {}),
        )
        for t in d.get("tools", [])
    ]
    return ToolSnapshot(
        snapshot_id=d.get("snapshot_id", str(uuid.uuid4())),
        task_type=d["task_type"],
        version=d.get("version", 1),
        tools=tools,
        avg_token_savings=d.get("avg_token_savings", 0.0),
        confidence=d.get("confidence", 0.0),
        sample_size=d.get("sample_size", 0),
        created_at=datetime.fromisoformat(d["created_at"]).replace(tzinfo=timezone.utc)
        if "created_at" in d
        else datetime.now(timezone.utc),
        tags=d.get("tags", []),
    )
