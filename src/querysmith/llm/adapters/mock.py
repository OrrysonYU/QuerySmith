"""Deterministic scripted LLM for tests."""

from collections import defaultdict, deque
from typing import Any, TypeVar

from pydantic import BaseModel

from querysmith.llm.client import LLMCallContext, PromptRef

T = TypeVar("T", bound=BaseModel)


class MockLLMClient:
    def __init__(self, scripts: dict[str, list[dict[str, Any]]]) -> None:
        self._scripts = defaultdict(deque, {key: deque(value) for key, value in scripts.items()})

    async def complete_structured(
        self,
        *,
        prompt: PromptRef,
        variables: dict[str, Any],
        response_model: type[T],
        context: LLMCallContext,
    ) -> T:
        del variables
        context.charge(1, 1)
        if not self._scripts[prompt.name]:
            raise RuntimeError(f"No scripted response for {prompt.name}")
        return response_model.model_validate(self._scripts[prompt.name].popleft())
