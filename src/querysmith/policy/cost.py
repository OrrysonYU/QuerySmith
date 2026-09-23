"""PostgreSQL EXPLAIN cost gate; never executes model SQL."""

import json
from typing import Any

from pydantic import BaseModel, Field


class CostVerdict(BaseModel):
    allowed: bool
    total_cost: float = Field(ge=0)
    threshold: float = Field(gt=0)


async def inspect_postgres_cost(connection: Any, sql: str, threshold: float) -> CostVerdict:
    plan_value = await connection.fetchval(f"EXPLAIN (FORMAT JSON, COSTS TRUE) {sql}")
    payload = json.loads(plan_value) if isinstance(plan_value, str) else plan_value
    total_cost = float(payload[0]["Plan"]["Total Cost"])
    return CostVerdict(allowed=total_cost <= threshold, total_cost=total_cost, threshold=threshold)
