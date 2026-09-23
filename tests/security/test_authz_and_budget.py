from uuid import uuid4

import pytest

from querysmith.llm.client import LLMCallContext
from querysmith.persistence.jobs import InMemoryJobRepository, JobRecord


@pytest.mark.security
@pytest.mark.asyncio
async def test_job_repository_hides_cross_user_existence() -> None:
    repository = InMemoryJobRepository()
    owner = uuid4()
    attacker = uuid4()
    job = await repository.create(JobRecord(user_id=owner, question="private"))
    assert await repository.get(job.id, attacker) is None
    assert not await repository.request_cancel(job.id, attacker)


@pytest.mark.security
def test_token_budget_rejects_before_additional_model_work() -> None:
    context = LLMCallContext(remaining_calls=0, remaining_tokens=10)
    with pytest.raises(RuntimeError, match="budget exhausted"):
        context.charge(1, 1)
