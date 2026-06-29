"""knowledge baseline (knowledge bases, sources, documents, chunks, tools)

Revision ID: knowledge_0001_baseline
Revises:
Create Date: 2026-06-29

Branch: knowledge. enterprise_id / user_id / role_id are logical references to
the platform tables (no cross-module FK).
"""

from alembic import op
import sqlalchemy as sa

revision = "knowledge_0001_baseline"
down_revision = None
branch_labels = ("knowledge",)
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kb_knowledge_bases",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kb_knowledge_bases_enterprise_id", "kb_knowledge_bases", ["enterprise_id"])

    op.create_table(
        "kb_role_grants",
        sa.Column("knowledge_base_id", sa.String(length=36), sa.ForeignKey("kb_knowledge_bases.id"), primary_key=True),
        sa.Column("role_id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "kb_data_sources",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=36), sa.ForeignKey("kb_knowledge_bases.id"), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kb_data_sources_enterprise_id", "kb_data_sources", ["enterprise_id"])
    op.create_index("ix_kb_data_sources_knowledge_base_id", "kb_data_sources", ["knowledge_base_id"])

    op.create_table(
        "kb_documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=36), sa.ForeignKey("kb_knowledge_bases.id"), nullable=False),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("kb_data_sources.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kb_documents_enterprise_id", "kb_documents", ["enterprise_id"])
    op.create_index("ix_kb_documents_knowledge_base_id", "kb_documents", ["knowledge_base_id"])

    op.create_table(
        "kb_chunks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("kb_documents.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("embedding_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kb_chunks_enterprise_id", "kb_chunks", ["enterprise_id"])
    op.create_index("ix_kb_chunks_document_id", "kb_chunks", ["document_id"])

    op.create_table(
        "kb_tools",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=36), sa.ForeignKey("kb_knowledge_bases.id"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("schema_json", sa.JSON(), nullable=True),
        sa.Column("endpoint_url", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kb_tools_enterprise_id", "kb_tools", ["enterprise_id"])
    op.create_index("ix_kb_tools_knowledge_base_id", "kb_tools", ["knowledge_base_id"])

    op.create_table(
        "kb_tool_role_grants",
        sa.Column("tool_id", sa.String(length=36), sa.ForeignKey("kb_tools.id"), primary_key=True),
        sa.Column("role_id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "kb_query_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=36), sa.ForeignKey("kb_knowledge_bases.id"), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kb_query_logs_enterprise_id", "kb_query_logs", ["enterprise_id"])
    op.create_index("ix_kb_query_logs_user_id", "kb_query_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_kb_query_logs_user_id", table_name="kb_query_logs")
    op.drop_index("ix_kb_query_logs_enterprise_id", table_name="kb_query_logs")
    op.drop_table("kb_query_logs")
    op.drop_table("kb_tool_role_grants")
    op.drop_index("ix_kb_tools_knowledge_base_id", table_name="kb_tools")
    op.drop_index("ix_kb_tools_enterprise_id", table_name="kb_tools")
    op.drop_table("kb_tools")
    op.drop_index("ix_kb_chunks_document_id", table_name="kb_chunks")
    op.drop_index("ix_kb_chunks_enterprise_id", table_name="kb_chunks")
    op.drop_table("kb_chunks")
    op.drop_index("ix_kb_documents_knowledge_base_id", table_name="kb_documents")
    op.drop_index("ix_kb_documents_enterprise_id", table_name="kb_documents")
    op.drop_table("kb_documents")
    op.drop_index("ix_kb_data_sources_knowledge_base_id", table_name="kb_data_sources")
    op.drop_index("ix_kb_data_sources_enterprise_id", table_name="kb_data_sources")
    op.drop_table("kb_data_sources")
    op.drop_table("kb_role_grants")
    op.drop_index("ix_kb_knowledge_bases_enterprise_id", table_name="kb_knowledge_bases")
    op.drop_table("kb_knowledge_bases")
