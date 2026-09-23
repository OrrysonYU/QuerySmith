from datetime import UTC, datetime, timedelta

import pytest

from querysmith.agent.error_taxonomy import FailureRoute, classify
from querysmith.agent.repair import ensure_unique_attempt
from querysmith.agent.state import Budgets, SqlAttempt
from querysmith.policy.verdicts import PolicyReason


def test_security_never_repairs() -> None:
    assert classify(policy_reason=PolicyReason.UNAUTHORIZED_TABLE).route is FailureRoute.BLOCK


def test_duplicate_and_budget_terminate() -> None:
    attempt = SqlAttempt(sql="SELECT 1", sql_hash="x")
    with pytest.raises(RuntimeError, match="Duplicate"):
        ensure_unique_attempt("x", [attempt])
    Budgets.with_deadline(datetime.now(UTC) + timedelta(seconds=10))
