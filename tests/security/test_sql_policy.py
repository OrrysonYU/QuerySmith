import pytest

from querysmith.policy.config import SqlPolicy
from querysmith.policy.engine import authorize

POLICY = SqlPolicy(allowed_tables=frozenset({"customer", "invoice"}))


@pytest.mark.security
@pytest.mark.parametrize(
    "sql",
    [
        "SELECT customer.id FROM customer; DROP TABLE customer",
        "SELECT * FROM customer",
        "SELECT pg_sleep(10) FROM customer",
        "SELECT secret.value FROM secret",
        "COPY customer TO '/tmp/x'",
        "UPDATE customer SET id = 1",
    ],
)
def test_adversarial_sql_is_rejected(sql: str) -> None:
    assert not authorize(sql, POLICY).ok
