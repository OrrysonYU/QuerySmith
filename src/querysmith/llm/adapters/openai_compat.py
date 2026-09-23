"""OpenAI-compatible structured-output adapter over HTTP."""

import asyncio
import json
import random
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from querysmith.llm.client import LLMCallContext, PromptRef
from querysmith.llm.prompts.registry import PromptRegistry

T = TypeVar("T", bound=BaseModel)


class LLMTransportError(RuntimeError):
    pass


class LLMMalformedOutput(RuntimeError):
    pass


class OpenAICompatibleAdapter:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        prompts: PromptRegistry,
        timeout: float = 30,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._model = model
        self._prompts = prompts
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def complete_structured(
        self,
        *,
        prompt: PromptRef,
        variables: dict[str, Any],
        response_model: type[T],
        context: LLMCallContext,
    ) -> T:
        rendered = self._prompts.render(prompt, variables)
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": rendered.system},
                {"role": "user", "content": rendered.user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": response_model.model_json_schema(),
                    "strict": True,
                },
            },
        }
        validation_feedback: str | None = None
        for malformed_attempt in range(2):
            if validation_feedback:
                payload["messages"].append(
                    {
                        "role": "user",
                        "content": f"Your prior JSON failed schema validation. Return corrected JSON only. Errors: {validation_feedback}",
                    }
                )
            response = await self._post_with_retry(payload)
            body = response.json()
            usage = body.get("usage", {})
            context.charge(
                int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
            )
            try:
                content = body["choices"][0]["message"]["content"]
                return response_model.model_validate_json(content)
            except (KeyError, IndexError, TypeError, ValidationError, json.JSONDecodeError) as exc:
                validation_feedback = str(exc)[:1000]
                if malformed_attempt == 1:
                    raise LLMMalformedOutput("Provider returned invalid structured output") from exc
        raise AssertionError("unreachable")

    async def _post_with_retry(self, payload: dict[str, Any]) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self._client.post("chat/completions", json=payload)
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if (
                    isinstance(exc, httpx.HTTPStatusError)
                    and exc.response.status_code < 500
                    and exc.response.status_code != 429
                ):
                    break
                if attempt < 2:
                    await asyncio.sleep((2**attempt) * 0.2 + random.random() * 0.1)
        raise LLMTransportError("LLM provider request failed") from last_error
