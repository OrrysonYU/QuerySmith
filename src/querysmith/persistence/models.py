"""Control-plane SQLAlchemy models mirroring the baseline migration."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lookup_hash: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    scopes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)


class DataSource(Base):
    __tablename__ = "data_sources"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    dialect: Mapped[str] = mapped_column(String(30))
    secret_reference: Mapped[str] = mapped_column(String(200))
    policy: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    summary: Mapped[str] = mapped_column(Text, default="")


class Query(Base):
    __tablename__ = "queries"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), index=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (
        Index("ix_queries_status_created", "status", "created_at"),
        Index(
            "uq_query_idempotency",
            "user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=idempotency_key.is_not(None),
        ),
    )


class QueryAttempt(Base):
    __tablename__ = "query_attempts"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    query_id: Mapped[UUID] = mapped_column(ForeignKey("queries.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    sql: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    __table_args__ = (UniqueConstraint("query_id", "sequence"),)


class TraceEvent(Base):
    __tablename__ = "trace_events"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    query_id: Mapped[UUID] = mapped_column(ForeignKey("queries.id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    __table_args__ = (Index("ix_trace_query_seq", "query_id", "sequence", unique=True),)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    actor_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SchemaSnapshotRecord(Base):
    __tablename__ = "schema_snapshots"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    data_source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id", ondelete="CASCADE"))
    signature: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    __table_args__ = (UniqueConstraint("data_source_id", "version"),)
