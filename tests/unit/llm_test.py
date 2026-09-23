import pytest
from pydantic import BaseModel

from querysmith.llm.adapters.mock import MockLLMClient
from querysmith.llm.client import LLMCallContext, PromptRef


class Answer(BaseModel):
    value: int


@pytest.mark.asyncio
async def test_mock_llm_is_typed_and_budgeted() -> None:
    client = MockLLMClient({"x": [{"value": 2}]})
    context = LLMCallContext()
    answer = await client.complete_structured(
        prompt=PromptRef("x", 1), variables={}, response_model=Answer, context=context
    )
    assert answer.value == 2 and context.remaining_calls == 9
