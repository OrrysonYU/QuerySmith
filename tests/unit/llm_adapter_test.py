import json
from pathlib import Path

import httpx
import pytest
from pydantic import BaseModel

from querysmith.llm.adapters.openai_compat import OpenAICompatibleAdapter
from querysmith.llm.client import LLMCallContext, PromptRef
from querysmith.llm.prompts.registry import PromptRegistry


class Answer(BaseModel):
    value: int


@pytest.mark.asyncio
async def test_openai_adapter_validates_structured_response_and_tokens() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["response_format"]["type"] == "json_schema"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"value": 7}'}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            },
        )

    adapter = OpenAICompatibleAdapter(
        base_url="https://example.invalid",
        api_key="secret",
        model="test",
        prompts=PromptRegistry(Path("prompts")),
        transport=httpx.MockTransport(handler),
    )
    context = LLMCallContext()
    result = await adapter.complete_structured(
        prompt=PromptRef("interpret_question", 1),
        variables={"question": "x", "conversation_summary": ""},
        response_model=Answer,
        context=context,
    )
    await adapter.close()
    assert result.value == 7
    assert context.prompt_tokens == 3 and context.completion_tokens == 2
