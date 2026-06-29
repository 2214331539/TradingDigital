"""Knowledge-base ORM models.

Cross-module references (enterprise_id, user_id, role_id) are logical foreign
keys — plain indexed strings with no DB-level constraint to the platform tables —
so the knowledge module stays self-contained. Intra-module relationships keep
real FKs.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, JSON, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column

from tradedigital.core.database import Base
from tradedigital.core.time import utc_now


def uuid_str() -> str:
    return str(uuid.uuid4())


kb_role_grants = Table(
    "kb_role_grants",
    Base.metadata,
    Column("knowledge_base_id", String(36), ForeignKey("kb_knowledge_bases.id"), primary_key=True),
    # role_id is a logical reference to platform iam_roles (no FK constraint).
    Column("role_id", String(36), primary_key=True),
    Column("created_at", DateTime(timezone=True), default=utc_now, nullable=False),
)


kb_tool_role_grants = Table(
    "kb_tool_role_grants",
    Base.metadata,
    Column("tool_id", String(36), ForeignKey("kb_tools.id"), primary_key=True),
    Column("role_id", String(36), primary_key=True),
    Column("created_at", DateTime(timezone=True), default=utc_now, nullable=False),
)


class TimestampMixin:
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class KnowledgeBase(Base, TimestampMixin):
    __tablename__ = "kb_knowledge_bases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)


class DataSource(Base, TimestampMixin):
    __tablename__ = "kb_data_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(String(36), index=True)
    knowledge_base_id: Mapped[str] = mapped_column(String(36), ForeignKey("kb_knowledge_bases.id"), index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class Document(Base, TimestampMixin):
    __tablename__ = "kb_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(String(36), index=True)
    knowledge_base_id: Mapped[str] = mapped_column(String(36), ForeignKey("kb_knowledge_bases.id"), index=True)
    source_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("kb_data_sources.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ready", nullable=False)


class Chunk(Base, TimestampMixin):
    __tablename__ = "kb_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(String(36), index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("kb_documents.id"), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    embedding_ref: Mapped[str | None] = mapped_column(Text, nullable=True)


class Tool(Base, TimestampMixin):
    __tablename__ = "kb_tools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(String(36), index=True)
    knowledge_base_id: Mapped[str] = mapped_column(String(36), ForeignKey("kb_knowledge_bases.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    endpoint_url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class QueryLog(Base):
    __tablename__ = "kb_query_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    knowledge_base_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("kb_knowledge_bases.id"), nullable=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
