"""Versioned schema-catalog persistence with enrichment preservation."""

from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from querysmith.caching.schema_cache import SchemaCache
from querysmith.persistence.models import SchemaSnapshotRecord
from querysmith.schema_intel.models import SchemaSnapshot


def preserve_enrichment(previous: SchemaSnapshot, current: SchemaSnapshot) -> SchemaSnapshot:
    prior_tables = {table.qualified_name: table for table in previous.tables}
    merged_tables = []
    for table in current.tables:
        prior = prior_tables.get(table.qualified_name)
        if prior is None:
            merged_tables.append(table)
            continue
        prior_columns = {column.name: column for column in prior.columns}
        columns = []
        for column in table.columns:
            old = prior_columns.get(column.name)
            columns.append(
                column.model_copy(
                    update={
                        "description": old.description,
                        "sensitive": old.sensitive,
                        "sample_values": old.sample_values,
                    }
                )
                if old
                else column
            )
        merged_tables.append(
            table.model_copy(update={"description": prior.description, "columns": columns})
        )
    return current.model_copy(update={"tables": merged_tables})


class SchemaCatalogService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        cache: SchemaCache,
        introspect: Callable[[], Awaitable[SchemaSnapshot]],
    ) -> None:
        self._sessions = sessions
        self._cache = cache
        self._introspect = introspect

    async def get_snapshot(self, data_source_id: UUID, source_name: str) -> SchemaSnapshot:
        async def loader() -> SchemaSnapshot:
            current = await self._introspect()
            previous = await self._latest(data_source_id)
            if previous and previous.signature == current.signature:
                return previous
            if previous:
                current = preserve_enrichment(previous, current)
            await self._persist(data_source_id, current)
            return current

        return await self._cache.get(source_name, loader)

    async def _latest(self, data_source_id: UUID) -> SchemaSnapshot | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(SchemaSnapshotRecord)
                .where(SchemaSnapshotRecord.data_source_id == data_source_id)
                .order_by(SchemaSnapshotRecord.version.desc())
                .limit(1)
            )
            return SchemaSnapshot.model_validate(row.snapshot) if row else None

    async def _persist(self, data_source_id: UUID, snapshot: SchemaSnapshot) -> None:
        async with self._sessions() as session, session.begin():
            latest = await session.scalar(
                select(func.max(SchemaSnapshotRecord.version)).where(
                    SchemaSnapshotRecord.data_source_id == data_source_id
                )
            )
            session.add(
                SchemaSnapshotRecord(
                    id=uuid4(),
                    data_source_id=data_source_id,
                    signature=snapshot.signature,
                    version=int(latest or 0) + 1,
                    snapshot=snapshot.model_dump(mode="json"),
                )
            )
