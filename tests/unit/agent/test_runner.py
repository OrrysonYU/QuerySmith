import asyncio
from uuid import uuid4

import pytest

from querysmith.agent.runner import JobRunner
from querysmith.agent.state import QueryStatus
from querysmith.persistence.jobs import InMemoryJobRepository, JobRecord


@pytest.mark.asyncio
async def test_runner_persists_terminal_state_and_reconciles_orphans() -> None:
    repository = InMemoryJobRepository()

    async def execute(job: JobRecord) -> dict[str, str]:
        return {"status": "SUCCEEDED", "answer": job.question}

    runner = JobRunner(repository, execute, max_concurrency=1)
    user_id = uuid4()
    job = await runner.submit(JobRecord(user_id=user_id, question="hello"))
    for _ in range(50):
        current = await repository.get(job.id, user_id)
        if current and current.status is QueryStatus.SUCCEEDED:
            break
        await asyncio.sleep(0.01)
    assert current and current.result and current.result["answer"] == "hello"
    orphan = JobRecord(user_id=user_id, question="orphan", status=QueryStatus.RUNNING)
    await repository.create(orphan)
    assert await runner.start() == 1
    assert (await repository.get(orphan.id, user_id)).status is QueryStatus.FAILED  # type: ignore[union-attr]
