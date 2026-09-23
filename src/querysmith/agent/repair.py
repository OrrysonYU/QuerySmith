"""Attempt-memory and duplicate controls for SQL repair."""

from querysmith.agent.state import SqlAttempt


def ensure_unique_attempt(
    candidate_hash: str, attempts: list[SqlAttempt], max_attempts: int = 3
) -> None:
    if len(attempts) >= max_attempts:
        raise RuntimeError("SQL attempt budget exhausted")
    if candidate_hash in {attempt.sql_hash for attempt in attempts}:
        raise RuntimeError("Duplicate SQL attempt rejected")


def repair_context(attempts: list[SqlAttempt]) -> list[dict[str, str | None]]:
    return [attempt.model_dump() for attempt in attempts]
