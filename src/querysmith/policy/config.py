"""SQL policy configuration."""

from pydantic import BaseModel, Field


class SqlPolicy(BaseModel):
    allowed_tables: frozenset[str] = Field(default_factory=frozenset)
    blocked_columns: frozenset[str] = Field(default_factory=frozenset)
    allowed_functions: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {
                "count",
                "sum",
                "avg",
                "min",
                "max",
                "coalesce",
                "cast",
                "date_trunc",
                "lower",
                "upper",
                "round",
            }
        )
    )
    max_rows: int = Field(1000, ge=1)
    require_limit: bool = True
    reject_select_star: bool = True
