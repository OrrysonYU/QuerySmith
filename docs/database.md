# Database

## Control plane

The app database is PostgreSQL through SQLAlchemy 2 async + asyncpg. Alembic migration
`0001_baseline` creates users, API keys, data sources, conversations, queries, attempts, events,
audit log, and versioned schema snapshots with ownership, sequence, status/time, and idempotency
indexes. Migrations run as a release step, never at application startup. Offline SQL compilation is
part of CI; live CI runs upgrade → downgrade → upgrade against PostgreSQL 16.

## Query sources

`ConnectionManager` owns independent pools. PostgreSQL connections set read-only transactions,
statement timeout, and pinned search path. SQLite support opens `mode=ro` and enables
`PRAGMA query_only`; it is not an app database. The Compose Chinook source creates a dedicated
`querysmith_ro` role with SELECT-only grants, default read-only transactions, and a timeout.

The executor streams rows through timeout, row, and byte caps. PostgreSQL cancellation propagates
through asyncpg task cancellation. Optional `EXPLAIN (FORMAT JSON, COSTS TRUE)` compares estimated
cost without executing the query; `EXPLAIN ANALYZE` is never used.
