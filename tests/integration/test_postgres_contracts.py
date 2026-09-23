"""Live PostgreSQL migration contracts, activated by an explicit isolated database URL."""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

pytestmark = pytest.mark.integration
DATABASE_URL = os.getenv("QS_TEST_POSTGRES_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="QS_TEST_POSTGRES_URL is not configured")
def test_migration_upgrade_downgrade_and_schema() -> None:
    assert DATABASE_URL
    sync_url = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
    config = Config(str(Path("alembic.ini")))
    config.set_main_option("sqlalchemy.url", sync_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(sync_url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert {
            "users",
            "api_keys",
            "data_sources",
            "queries",
            "query_attempts",
            "trace_events",
            "audit_log",
            "schema_snapshots",
        }.issubset(tables)
    finally:
        engine.dispose()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
