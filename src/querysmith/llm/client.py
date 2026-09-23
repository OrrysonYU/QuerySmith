"""Provider-neutral structured LLM boundary."""

from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class PromptRef:
    name: str
    version: int


@dataclass
class LLMCallContext:
    remaining_calls: int = 10
    remaining_tokens: int = 60_000
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def charge(self, prompt: int, completion: int) -> None:
        if self.remaining_calls <= 0 or prompt + completion > self.remaining_tokens:
            raise RuntimeError("LLM budget exhausted")
        self.remaining_calls -= 1
        self.remaining_tokens -= prompt + completion
        self.prompt_tokens += prompt
        self.completion_tokens += completion


class LLMClient(Protocol):
    async def complete_structured(
        self,
        *,
        prompt: PromptRef,
        variables: dict[str, Any],
        response_model: type[T],
        context: LLMCallContext,
    ) -> T: ...
