import json
from pathlib import Path

import pytest

from querysmith.policy.config import SqlPolicy
from querysmith.policy.engine import authorize

CASES = json.loads(Path("tests/security/corpus/sql_cases.json").read_text(encoding="utf-8"))
POLICY = SqlPolicy(allowed_tables=frozenset({"customer"}))


@pytest.mark.security
@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_adversarial_sql_corpus_is_rejected(case: dict[str, str]) -> None:
    verdict = authorize(case["sql"], POLICY)
    assert not verdict.ok, f"unexpectedly authorized: {case['sql']}"
