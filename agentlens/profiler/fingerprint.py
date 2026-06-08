from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaskFingerprint:
    fingerprint_id: str
    task_type: str
    signals: list[str]
    tool_pattern: list[str]
    confidence_threshold: float


class FingerprintMatcher:
    def __init__(self, fingerprints: list[TaskFingerprint]) -> None:
        self._fingerprints = fingerprints

    def match(self, text: str) -> str | None:
        lower = text.lower()
        best_task: str | None = None
        best_score = 0.0

        for fp in self._fingerprints:
            hits = sum(1 for s in fp.signals if s.lower() in lower)
            if hits == 0:
                continue
            score = hits / len(fp.signals)
            # Accept if score meets the confidence threshold, or if no
            # better match has been found yet (score > 0 is sufficient
            # when there is no competing fingerprint above threshold).
            qualifies = score >= fp.confidence_threshold or (
                best_task is None and score > 0
            )
            if qualifies and score > best_score:
                best_score = score
                best_task = fp.task_type

        return best_task
