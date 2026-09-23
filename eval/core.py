"""Provider-independent, reproducible evaluation runner."""

import json
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    id: str
    question: str
    expected_status: str | None = None
    expected_shape: dict[str, Any] | None = None
    forbidden_constructs: list[str] = Field(default_factory=list)


class EvalRecord(BaseModel):
    id: str
    status: str
    attempts: int
    latency_ms: float
    first_attempt_failed: bool = False
    adversarial: bool = False
    golden_defined: bool = False
    golden_match: bool = False
    sql_safe: bool = True
    visualization_valid: bool | None = None
    error: str | None = None


RunCase = Callable[[EvalCase], Awaitable[dict[str, Any]]]


def load_cases(path: Path) -> list[EvalCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [EvalCase.model_validate(item) for item in payload]


class EvalRunner:
    def __init__(self, run_case: RunCase) -> None:
        self._run_case = run_case

    async def run(self, cases: list[EvalCase], *, adversarial: bool = False) -> list[EvalRecord]:
        records: list[EvalRecord] = []
        for case in cases:
            started = time.perf_counter()
            try:
                result = await self._run_case(case)
                status = str(result.get("status", "FAILED"))
                records.append(
                    EvalRecord(
                        id=case.id,
                        status=status,
                        attempts=int(result.get("attempts", 0)),
                        latency_ms=(time.perf_counter() - started) * 1000,
                        first_attempt_failed=bool(result.get("first_attempt_failed", False)),
                        adversarial=adversarial,
                        golden_defined="golden_match" in result,
                        golden_match=bool(result.get("golden_match", False)),
                        sql_safe=bool(result.get("sql_safe", True)),
                        visualization_valid=result.get("visualization_valid"),
                    )
                )
            except Exception as exc:
                records.append(
                    EvalRecord(
                        id=case.id,
                        status="FAILED",
                        attempts=0,
                        latency_ms=(time.perf_counter() - started) * 1000,
                        adversarial=adversarial,
                        error=type(exc).__name__,
                    )
                )
        return records
