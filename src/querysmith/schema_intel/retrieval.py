"""Deterministic permission-first schema retrieval."""

import re

from pydantic import BaseModel

from querysmith.schema_intel.models import RelationshipInfo, SchemaSnapshot, TableInfo


class SchemaSubset(BaseModel):
    tables: list[TableInfo]
    relationships: list[RelationshipInfo]


def select_candidates(
    snapshot: SchemaSnapshot,
    question: str,
    allowed_tables: frozenset[str],
    blocked_columns: frozenset[str] = frozenset(),
    max_tables: int = 8,
) -> SchemaSubset:
    terms = set(re.findall(r"[a-z0-9_]+", question.lower()))
    allowed = {name.lower() for name in allowed_tables}
    blocked = {name.lower() for name in blocked_columns}
    scored: list[tuple[int, TableInfo]] = []
    for table in snapshot.tables:
        if table.qualified_name.lower() not in allowed and table.name.lower() not in allowed:
            continue
        columns = [
            c
            for c in table.columns
            if f"{table.name.lower()}.{c.name.lower()}" not in blocked
            and c.name.lower() not in blocked
        ]
        safe_table = table.model_copy(
            update={
                "columns": [
                    c.model_copy(update={"sample_values": []}) if c.sensitive else c
                    for c in columns
                ]
            }
        )
        haystack = " ".join([table.name, table.description, *(c.name for c in columns)]).lower()
        score = sum(1 for term in terms if term in haystack)
        scored.append((score, safe_table))
    scored.sort(key=lambda item: (-item[0], item[1].name))
    selected = [item[1] for item in scored[:max_tables] if item[0] > 0] or [
        item[1] for item in scored[:max_tables]
    ]
    names = {table.qualified_name for table in selected} | {table.name for table in selected}
    relationships = [
        rel
        for rel in snapshot.relationships
        if rel.source_table in names and rel.target_table in names
    ]
    return SchemaSubset(tables=selected, relationships=relationships)
