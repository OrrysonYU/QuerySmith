"""Dialect-aware asynchronous PostgreSQL catalog introspection."""

from typing import Any

from querysmith.schema_intel.models import (
    ColumnInfo,
    RelationshipInfo,
    SchemaSnapshot,
    TableInfo,
)


async def introspect_postgres(connection: Any, source: str) -> SchemaSnapshot:
    primary_rows = await connection.fetch(
        """
        SELECT tc.table_schema, tc.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
        """
    )
    primary_keys = {
        (str(row["table_schema"]), str(row["table_name"]), str(row["column_name"]))
        for row in primary_rows
    }
    estimate_rows = await connection.fetch(
        """
        SELECT n.nspname AS table_schema, c.relname AS table_name,
               GREATEST(c.reltuples::bigint, 0) AS row_estimate
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r', 'p')
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        """
    )
    estimates = {
        (str(row["table_schema"]), str(row["table_name"])): int(row["row_estimate"])
        for row in estimate_rows
    }
    rows = await connection.fetch(
        """
        SELECT c.table_schema, c.table_name, c.column_name, c.data_type, c.is_nullable
        FROM information_schema.columns c
        WHERE c.table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY c.table_schema, c.table_name, c.ordinal_position
        """
    )
    grouped: dict[tuple[str, str], list[ColumnInfo]] = {}
    for row in rows:
        schema = str(row["table_schema"])
        table = str(row["table_name"])
        column = str(row["column_name"])
        grouped.setdefault((schema, table), []).append(
            ColumnInfo(
                name=column,
                data_type=str(row["data_type"]),
                nullable=row["is_nullable"] == "YES",
                primary_key=(schema, table, column) in primary_keys,
            )
        )
    tables = [
        TableInfo(
            name=name,
            schema_name=schema,
            columns=columns,
            row_estimate=estimates.get((schema, name)),
        )
        for (schema, name), columns in grouped.items()
    ]
    fk_rows = await connection.fetch(
        """
        SELECT tc.table_schema, tc.table_name, kcu.column_name,
               ccu.table_schema AS foreign_table_schema,
               ccu.table_name AS foreign_table_name,
               ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        """
    )
    relationships = [
        RelationshipInfo(
            source_table=f"{row['table_schema']}.{row['table_name']}",
            source_column=str(row["column_name"]),
            target_table=f"{row['foreign_table_schema']}.{row['foreign_table_name']}",
            target_column=str(row["foreign_column_name"]),
        )
        for row in fk_rows
    ]
    return SchemaSnapshot(
        source=source, tables=tables, relationships=relationships
    ).with_signature()
