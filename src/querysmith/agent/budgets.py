"""Deterministic deadline and attempt gates."""

from datetime import UTC, datetime

from querysmith.agent.state import Budgets, SqlAttempt


def assert_budget(budgets: Budgets, attempts: list[SqlAttempt]) -> None:
    if datetime.now(UTC) >= budgets.deadline:
        raise TimeoutError("request deadline exceeded")
    if len(attempts) >= budgets.max_attempts:
        raise RuntimeError("SQL attempt budget exhausted")
