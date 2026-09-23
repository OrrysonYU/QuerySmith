"""Portable schema catalog structures."""

from hashlib import sha256

from pydantic import BaseModel, Field


class ColumnInfo(BaseModel):
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    description: str = ""
    sensitive: bool = False
    sample_values: list[str] = Field(default_factory=list)


class TableInfo(BaseModel):
    name: str
    schema_name: str | None = None
    description: str = ""
    columns: list[ColumnInfo]
    row_estimate: int | None = None

    @property
    def qualified_name(self) -> str:
        return f"{self.schema_name}.{self.name}" if self.schema_name else self.name


class RelationshipInfo(BaseModel):
    source_table: str
    source_column: str
    target_table: str
    target_column: str


class SchemaSnapshot(BaseModel):
    source: str
    tables: list[TableInfo]
    relationships: list[RelationshipInfo] = Field(default_factory=list)
    signature: str = ""

    def with_signature(self) -> "SchemaSnapshot":
        payload = "|".join(
            sorted(
                f"{t.qualified_name}:{c.name}:{c.data_type}" for t in self.tables for c in t.columns
            )
        )
        return self.model_copy(update={"signature": sha256(payload.encode()).hexdigest()})
