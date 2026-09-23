"""Create the QuerySmith control-plane schema."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lookup_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("scopes", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_table(
        "data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("dialect", sa.String(30), nullable=False),
        sa.Column("secret_reference", sa.String(200), nullable=False),
        sa.Column("policy", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id"),
            nullable=True,
        ),
        sa.Column("idempotency_key", sa.String(200), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_queries_status_created", "queries", ["status", "created_at"])
    op.create_index(
        "uq_query_idempotency",
        "queries",
        ["user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.create_table(
        "query_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "query_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("queries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("sql", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("query_id", "sequence"),
    )
    op.create_table(
        "trace_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "query_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("queries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("query_id", "sequence"),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "schema_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "data_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("signature", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("data_source_id", "version"),
    )


def downgrade() -> None:
    for table in (
        "schema_snapshots",
        "audit_log",
        "trace_events",
        "query_attempts",
        "queries",
        "conversations",
        "data_sources",
        "api_keys",
        "users",
    ):
        op.drop_table(table)
