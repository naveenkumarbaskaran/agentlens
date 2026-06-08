from __future__ import annotations

from agentlens.profiler.fingerprint import FingerprintMatcher


class TaskClassifier:
    """
    Classifies a user message into a known task type using a lightweight LLM.
    Falls back to FingerprintMatcher (signal-based) when the LLM call fails.

    Usage:
        classifier = TaskClassifier(
            known_task_types=["code-review", "db-query"],
            model="claude-haiku-4-5-20251001",
        )
        task_type = await classifier.classify("Please review this PR")
        # → "code-review"
    """

    def __init__(
        self,
        known_task_types: list[str],
        model: str = "claude-haiku-4-5-20251001",
        fallback_matcher: FingerprintMatcher | None = None,
        max_tokens: int = 20,
    ) -> None:
        self._known = known_task_types
        self._model = model
        self._fallback = fallback_matcher
        self._max_tokens = max_tokens

    def _build_prompt(self, message: str) -> str:
        types_list = "\n".join(f"- {t}" for t in self._known)
        return (
            f"Classify the following user message into exactly one of these task types.\n"
            f"Respond with ONLY the task type string, nothing else.\n"
            f"If none fit, respond with: none\n\n"
            f"Task types:\n{types_list}\n\n"
            f"User message: {message}\n\n"
            f"Task type:"
        )

    async def _call_llm(self, prompt: str) -> str:
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip().lower()

    async def classify(self, message: str) -> str | None:
        try:
            prompt = self._build_prompt(message)
            raw = await self._call_llm(prompt)
            if raw in self._known:
                return raw
            return None
        except Exception:
            if self._fallback is not None:
                return self._fallback.match(message)
            return None
