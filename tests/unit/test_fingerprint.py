# tests/unit/test_fingerprint.py
from agentlens.profiler.fingerprint import FingerprintMatcher, TaskFingerprint


def test_match_by_signal():
    fingerprints = [
        TaskFingerprint(
            fingerprint_id="fp1",
            task_type="code-review",
            signals=["review", "pull request", "pr", "diff"],
            tool_pattern=[],
            confidence_threshold=0.6,
        ),
        TaskFingerprint(
            fingerprint_id="fp2",
            task_type="db-query",
            signals=["query", "database", "sql", "table"],
            tool_pattern=[],
            confidence_threshold=0.6,
        ),
    ]
    matcher = FingerprintMatcher(fingerprints)
    result = matcher.match("Please review this pull request carefully")
    assert result == "code-review"


def test_match_returns_none_on_no_match():
    fingerprints = [
        TaskFingerprint(
            fingerprint_id="fp1",
            task_type="code-review",
            signals=["review", "pr", "diff"],
            tool_pattern=[],
            confidence_threshold=0.6,
        ),
    ]
    matcher = FingerprintMatcher(fingerprints)
    result = matcher.match("What is the weather today?")
    assert result is None


def test_match_picks_highest_signal_count():
    fingerprints = [
        TaskFingerprint(
            fingerprint_id="fp1",
            task_type="code-review",
            signals=["review", "diff", "pr"],
            tool_pattern=[],
            confidence_threshold=0.3,
        ),
        TaskFingerprint(
            fingerprint_id="fp2",
            task_type="db-query",
            signals=["review", "query", "sql"],
            tool_pattern=[],
            confidence_threshold=0.3,
        ),
    ]
    matcher = FingerprintMatcher(fingerprints)
    result = matcher.match("review the diff and check the query")
    assert result is not None
