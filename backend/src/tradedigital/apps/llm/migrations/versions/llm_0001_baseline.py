"""llm baseline (models, presets, projects, conversations, messages)

Revision ID: llm_0001_baseline
Revises:
Create Date: 2026-06-29

Branch: llm. enterprise_id / user_id / role_id are logical references to the
platform tables (no cross-module FK), so this module can own its own database.
"""

from alembic import op
import sqlalchemy as sa

revision = "llm_0001_baseline"
down_revision = None
branch_labels = ("llm",)
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_models",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider_code", sa.String(length=64), nullable=False),
        sa.Column("model_key", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("api_key_ref", sa.String(length=128), nullable=False),
        sa.Column("context_length", sa.Integer(), nullable=False),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False),
        sa.Column("default_temperature", sa.Numeric(3, 2), nullable=False),
        sa.Column("support_streaming", sa.Boolean(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "llm_model_role_grants",
        sa.Column("model_id", sa.String(length=36), sa.ForeignKey("llm_models.id"), primary_key=True),
        sa.Column("role_id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "llm_assistant_presets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("default_model_id", sa.String(length=36), sa.ForeignKey("llm_models.id"), nullable=True),
        sa.Column("icon", sa.String(length=64), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_assistant_presets_enterprise_id", "llm_assistant_presets", ["enterprise_id"])

    op.create_table(
        "llm_projects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_projects_enterprise_id", "llm_projects", ["enterprise_id"])
    op.create_index("ix_llm_projects_user_id", "llm_projects", ["user_id"])

    op.create_table(
        "llm_conversations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("assistant_preset_id", sa.String(length=36), sa.ForeignKey("llm_assistant_presets.id"), nullable=True),
        sa.Column("model_id", sa.String(length=36), sa.ForeignKey("llm_models.id"), nullable=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("llm_projects.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("temporary", sa.Boolean(), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_conversations_enterprise_id", "llm_conversations", ["enterprise_id"])
    op.create_index("ix_llm_conversations_user_id", "llm_conversations", ["user_id"])

    op.create_table(
        "llm_messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), sa.ForeignKey("llm_conversations.id"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("model_id", sa.String(length=36), sa.ForeignKey("llm_models.id"), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_messages_enterprise_id", "llm_messages", ["enterprise_id"])
    op.create_index("ix_llm_messages_conversation_id", "llm_messages", ["conversation_id"])

    op.create_table(
        "llm_model_call_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), sa.ForeignKey("llm_conversations.id"), nullable=True),
        sa.Column("model_id", sa.String(length=36), sa.ForeignKey("llm_models.id"), nullable=True),
        sa.Column("provider_code", sa.String(length=64), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_model_call_logs_enterprise_id", "llm_model_call_logs", ["enterprise_id"])
    op.create_index("ix_llm_model_call_logs_user_id", "llm_model_call_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_model_call_logs_user_id", table_name="llm_model_call_logs")
    op.drop_index("ix_llm_model_call_logs_enterprise_id", table_name="llm_model_call_logs")
    op.drop_table("llm_model_call_logs")
    op.drop_index("ix_llm_messages_conversation_id", table_name="llm_messages")
    op.drop_index("ix_llm_messages_enterprise_id", table_name="llm_messages")
    op.drop_table("llm_messages")
    op.drop_index("ix_llm_conversations_user_id", table_name="llm_conversations")
    op.drop_index("ix_llm_conversations_enterprise_id", table_name="llm_conversations")
    op.drop_table("llm_conversations")
    op.drop_index("ix_llm_projects_user_id", table_name="llm_projects")
    op.drop_index("ix_llm_projects_enterprise_id", table_name="llm_projects")
    op.drop_table("llm_projects")
    op.drop_index("ix_llm_assistant_presets_enterprise_id", table_name="llm_assistant_presets")
    op.drop_table("llm_assistant_presets")
    op.drop_table("llm_model_role_grants")
    op.drop_table("llm_models")
