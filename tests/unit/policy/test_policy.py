import pytest

from querysmith.policy.config import SqlPolicy
from querysmith.policy.engine import authorize
from querysmith.policy.parser import validate_structure
from querysmith.policy.verdicts import PolicyReason

POLICY = SqlPolicy(
    allowed_tables=frozenset({"public.customer", "customer"}),
    blocked_columns=frozenset({"customer.email"}),
    max_rows=10,
)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE customer",
        "SELECT 1; DELETE FROM customer",
        "UPDATE customer SET x=1",
        "SELECT 1 INTO x",
    ],
)
def test_dangerous_sql_rejected(sql: str) -> None:
    assert not validate_structure(sql).ok


def test_limit_is_injected_and_hash_is_stable() -> None:
    verdict = authorize("SELECT customer.id FROM customer", POLICY)
    assert verdict.ok and verdict.rewritten_sql and "LIMIT 10" in verdict.rewritten_sql
    assert verdict.sql_hash == authorize("SELECT customer.id FROM customer", POLICY).sql_hash


def test_forbidden_table_and_column_are_rejected() -> None:
    assert authorize("SELECT users.id FROM users", POLICY).reason is PolicyReason.UNAUTHORIZED_TABLE
    assert (
        authorize("SELECT customer.email FROM customer", POLICY).reason
        is PolicyReason.BLOCKED_COLUMN
    )
    assert authorize("SELECT email FROM customer", POLICY).reason is PolicyReason.BLOCKED_COLUMN


def test_cte_is_not_treated_as_physical_table() -> None:
    verdict = authorize("WITH c AS (SELECT customer.id FROM customer) SELECT c.id FROM c", POLICY)
    assert verdict.ok
