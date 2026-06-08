# tests/unit/test_classifier.py
from unittest.mock import AsyncMock, patch
import pytest
from agentlens.profiler.classifier import TaskClassifier


def test_classifier_returns_known_task_type():
    classifier = TaskClassifier(
        known_task_types=["code-review", "db-query", "deploy"],
        model="claude-haiku-4-5-20251001",
    )
    with patch.object(classifier, "_call_llm", new=AsyncMock(return_value="code-review")):
        import asyncio
        result = asyncio.run(classifier.classify("Please review this pull request"))
    assert result == "code-review"


def test_classifier_returns_none_for_unknown():
    classifier = TaskClassifier(
        known_task_types=["code-review", "db-query"],
        model="claude-haiku-4-5-20251001",
    )
    with patch.object(classifier, "_call_llm", new=AsyncMock(return_value="unknown")):
        import asyncio
        result = asyncio.run(classifier.classify("What is the weather?"))
    assert result is None


def test_classifier_falls_back_to_fingerprint_on_error():
    from agentlens.profiler.fingerprint import FingerprintMatcher, TaskFingerprint
    fingerprints = [
        TaskFingerprint(
            fingerprint_id="fp1",
            task_type="code-review",
            signals=["review", "pull request"],
            tool_pattern=[],
            confidence_threshold=0.4,
        )
    ]
    classifier = TaskClassifier(
        known_task_types=["code-review"],
        model="claude-haiku-4-5-20251001",
        fallback_matcher=FingerprintMatcher(fingerprints),
    )
    with patch.object(classifier, "_call_llm", new=AsyncMock(side_effect=Exception("API error"))):
        import asyncio
        result = asyncio.run(classifier.classify("Please review this pull request"))
    assert result == "code-review"


def test_classifier_prompt_contains_task_types():
    classifier = TaskClassifier(
        known_task_types=["code-review", "db-query", "deploy"],
        model="claude-haiku-4-5-20251001",
    )
    prompt = classifier._build_prompt("review my PR")
    assert "code-review" in prompt
    assert "db-query" in prompt
    assert "deploy" in prompt
    assert "review my PR" in prompt
